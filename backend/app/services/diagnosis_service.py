import os
import hashlib
import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.run import (
    Run, DiagnosisModel, PatchApproval, ApprovalStatus, RunStatus, EvidenceModel
)
from backend.app.evidence.schema import EvidenceRecord
from backend.app.diagnostics.router import DeterministicRouter
from backend.app.repository.indexer import RepositoryIndexer
from backend.app.repository.validator import SourceValidator
from backend.app.optimization.synthesis_agent import PatchSynthesisAgent
from backend.app.optimization.critic_agent import SafetyCriticAgent
from backend.app.core.state_machine import transition_run_state

logger = logging.getLogger("perfpilot.diagnosis")

class DiagnosisService:
    @classmethod
    def compute_patch_hash(cls, patch_diff: str) -> str:
        """
        Cryptographic SHA-256 hash of the normalized patch diff.
        """
        normalized = patch_diff.strip().replace("\r\n", "\n")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def collect_source_context(
        cls,
        repo_path: str,
        target_url: str = "",
        max_files: int = 5
    ) -> Dict[str, str]:
        """
        Gathers source code context prioritizing the targeted route handler.
        """
        return RepositoryIndexer.collect_source_context(
            repo_path=repo_path,
            target_url=target_url,
            max_files=max_files
        )

    @classmethod
    async def diagnose_run(
        cls,
        db: AsyncSession,
        run: Run,
        baseline_metrics: Dict[str, Any]
    ) -> Optional[DiagnosisModel]:
        """
        Multi-agent diagnostic pipeline:
        1. Router selects diagnostic workers.
        2. Workers gather empirical EvidenceRecords.
        3. AST Indexer locates route handler and attributes bottleneck.
        4. Synthesis Agent generates minimal unified diff.
        5. Safety Critic evaluates risks and formulates regression test plan.
        6. SourceValidator verifies referenced files physically exist.
        7. Persists evidence, diagnosis, and awaits human approval.
        """
        # Step 1: Evaluate baseline SLA via Deterministic Router
        router_eval = DeterministicRouter.evaluate_baseline(
            baseline_metrics=baseline_metrics,
            objectives=run.objectives or {},
            target_type=run.target_type
        )

        # Check for Rule A short-circuit: Baseline already meets SLA
        if router_eval.should_short_circuit:
            logger.info(f"Run {run.id} short-circuited: {router_eval.reason}")
            # Persist an evidence record documenting SLA satisfaction
            evidence_rec = EvidenceRecord(
                run_id=run.id,
                category="router",
                observation=router_eval.reason,
                measured_values=baseline_metrics,
                source_type="http_metric",
                provenance="deterministic_router"
            )
            ev_model = EvidenceModel(
                evidence_id=evidence_rec.evidence_id,
                run_id=run.id,
                category=evidence_rec.category,
                observation=evidence_rec.observation,
                measured_values=evidence_rec.measured_values,
                source_type=evidence_rec.source_type,
                provenance=evidence_rec.provenance
            )
            db.add(ev_model)
            await db.commit()

            await transition_run_state(
                db=db,
                run=run,
                target_status=RunStatus.COMPLETED,
                message=router_eval.reason,
                details={"short_circuited": True}
            )
            return None

        # Step 2: Execute selected diagnostic workers to collect evidence
        evidence_records: List[EvidenceRecord] = []
        for worker in router_eval.selected_workers:
            try:
                worker_records = await worker.investigate(
                    run_id=run.id,
                    target_url=run.target_url,
                    repo_path=run.repo_path,
                    baseline_metrics=baseline_metrics
                )
                evidence_records.extend(worker_records)
            except Exception as e:
                logger.warning(f"Diagnostic worker {worker.name} encountered error: {e}")

        # Step 3: AST Source Attribution (Agent 4)
        handler_info = RepositoryIndexer.locate_route_handler(run.repo_path, run.target_url)
        supporting_locations = []
        if handler_info:
            supporting_locations.append({
                "file_path": handler_info["file_path"],
                "start_line": handler_info["start_line"],
                "end_line": handler_info["end_line"],
                "snippet": handler_info["snippet"],
                "explanation": f"AST indexed route handler '{handler_info['symbol']}' handling path '{handler_info['matched_path']}'"
            })
            evidence_records.append(
                EvidenceRecord(
                    run_id=run.id,
                    category="repository",
                    observation=f"AST route indexer attributed target URL to handler '{handler_info['symbol']}' in {handler_info['file_path']}:{handler_info['start_line']}-{handler_info['end_line']}.",
                    measured_values={"start_line": handler_info["start_line"], "end_line": handler_info["end_line"]},
                    source_type="ast_parser",
                    source_references=[supporting_locations[0]],
                    provenance="ast_symbol_indexer"
                )
            )

        # Persist all evidence records to database
        for rec in evidence_records:
            ev_model = EvidenceModel(
                evidence_id=rec.evidence_id,
                run_id=run.id,
                finding_id=rec.finding_id,
                category=rec.category,
                observation=rec.observation,
                measured_values=rec.measured_values,
                unit=rec.unit,
                source_type=rec.source_type,
                artifact_reference=rec.artifact_reference,
                trace_id=rec.trace_id,
                span_id=rec.span_id,
                timestamp=rec.timestamp.replace(tzinfo=None) if rec.timestamp.tzinfo else rec.timestamp,
                git_commit=rec.git_commit,
                environment_fingerprint=rec.environment_fingerprint,
                collection_method=rec.collection_method,
                tool_version=rec.tool_version,
                source_references=rec.source_references,
                provenance=rec.provenance,
                limitations=rec.limitations
            )
            db.add(ev_model)
        await db.commit()

        # Step 4: Source context collection
        source_context = cls.collect_source_context(run.repo_path, target_url=run.target_url)

        # Step 5: Patch Synthesis Agent (Agent 5)
        synthesis = await PatchSynthesisAgent.synthesize_patch(
            evidence_records=evidence_records,
            source_context=source_context,
            target_endpoint=run.target_url,
            user_objectives=run.objectives or {}
        )

        proposed_patch = synthesis.get("proposed_patch_diff", "")
        patch_hash = cls.compute_patch_hash(proposed_patch)

        # Step 6: Safety Critic Agent (Agent 6)
        critic = await SafetyCriticAgent.review_patch(
            proposed_patch_diff=proposed_patch,
            affected_files=synthesis.get("affected_files", []),
            evidence_records=evidence_records,
            source_context=source_context,
            target_endpoint=run.target_url
        )

        # Step 7: Filter and physically validate code locations
        validated_locations = SourceValidator.filter_valid_references(run.repo_path, supporting_locations)

        # Step 8: Persist DiagnosisModel
        stmt = select(DiagnosisModel).where(DiagnosisModel.run_id == run.id)
        res = await db.execute(stmt)
        diag = res.scalar_one_or_none()

        if not diag:
            diag = DiagnosisModel(
                run_id=run.id,
                summary=synthesis.get("summary", "Performance optimization patch"),
                symptoms=critic.get("observed_symptoms", ["Latency elevated during load test"]),
                ranked_hypotheses=critic.get("ranked_hypotheses", []),
                supporting_measurements=baseline_metrics,
                supporting_code_locations=validated_locations,
                confidence_score=critic.get("confidence_score", 0.85),
                uncertainty_notes=critic.get("uncertainty_notes", ""),
                proposed_patch_diff=proposed_patch,
                patch_hash=patch_hash,
                affected_files=synthesis.get("affected_files", []),
                expected_benefit=synthesis.get("expected_benefits", ""),
                risks=critic.get("potential_risks", []),
                regression_test_plan=critic.get("required_regression_tests", [])
            )
            db.add(diag)
        else:
            diag.summary = synthesis.get("summary", "Performance optimization patch")
            diag.symptoms = critic.get("observed_symptoms", [])
            diag.ranked_hypotheses = critic.get("ranked_hypotheses", [])
            diag.supporting_measurements = baseline_metrics
            diag.supporting_code_locations = validated_locations
            diag.confidence_score = critic.get("confidence_score", 0.85)
            diag.uncertainty_notes = critic.get("uncertainty_notes", "")
            diag.proposed_patch_diff = proposed_patch
            diag.patch_hash = patch_hash
            diag.affected_files = synthesis.get("affected_files", [])
            diag.expected_benefit = synthesis.get("expected_benefits", "")
            diag.risks = critic.get("potential_risks", [])
            diag.regression_test_plan = critic.get("required_regression_tests", [])

        # Create or reset PatchApproval gate
        stmt_app = select(PatchApproval).where(PatchApproval.run_id == run.id)
        res_app = await db.execute(stmt_app)
        approval = res_app.scalar_one_or_none()

        if not approval:
            approval = PatchApproval(
                run_id=run.id,
                status=ApprovalStatus.PENDING.value,
                patch_hash=patch_hash
            )
            db.add(approval)
        else:
            approval.status = ApprovalStatus.PENDING.value
            approval.patch_hash = patch_hash
            approval.reviewed_by = None
            approval.decision_reason = None
            approval.decided_at = None

        await db.commit()

        # Step 9: State transition to AWAITING_APPROVAL
        await transition_run_state(
            db=db,
            run=run,
            target_status=RunStatus.AWAITING_APPROVAL,
            message="Evidence gathered and patch synthesized; awaiting human approval gate",
            details={
                "patch_hash": patch_hash,
                "affected_files": synthesis.get("affected_files", []),
                "evidence_count": len(evidence_records)
            }
        )

        return diag
