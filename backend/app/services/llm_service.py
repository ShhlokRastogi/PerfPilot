import os
import json
import logging
from typing import Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.schemas.diagnosis import StructuredDiagnosisOutput, HypothesisItem, CodeLocation
from backend.app.evidence.schema import EvidenceRecord
from backend.app.optimization.synthesis_agent import PatchSynthesisAgent
from backend.app.optimization.critic_agent import SafetyCriticAgent

logger = logging.getLogger("perfpilot.llm")

class LLMServiceError(Exception):
    pass

class LLMService:
    @classmethod
    async def generate_diagnosis(
        cls,
        benchmark_metrics: Dict[str, Any],
        source_context: Dict[str, str],
        target_endpoint: str,
        user_objectives: Optional[Dict[str, Any]] = None,
        force_mock: bool = False
    ) -> StructuredDiagnosisOutput:
        """
        Coordinates multi-agent patch synthesis and safety evaluation.
        """
        if settings.GROQ_API_KEY:
            os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY

        # Synthesize initial EvidenceRecord from metrics
        p95_ms = float(benchmark_metrics.get("p95_latency_ms", 0.0))
        rps = float(benchmark_metrics.get("throughput_rps", 0.0))
        error_rate = float(benchmark_metrics.get("error_rate_pct", 0.0))

        initial_evidence = [
            EvidenceRecord(
                run_id="adhoc",
                category="backend",
                observation=f"Baseline load test measured p95 latency of {p95_ms:.1f}ms and throughput of {rps:.1f} req/s with {error_rate:.2f}% error rate.",
                measured_values=benchmark_metrics,
                source_type="http_metric"
            )
        ]

        try:
            # Agent 5: Patch Synthesis
            synthesis = await PatchSynthesisAgent.synthesize_patch(
                evidence_records=initial_evidence,
                source_context=source_context,
                target_endpoint=target_endpoint,
                user_objectives=user_objectives or {}
            )

            # Agent 6: Safety Critic
            critic = await SafetyCriticAgent.review_patch(
                proposed_patch_diff=synthesis.get("proposed_patch_diff", ""),
                affected_files=synthesis.get("affected_files", []),
                evidence_records=initial_evidence,
                source_context=source_context,
                target_endpoint=target_endpoint
            )

            raw_hypotheses = critic.get("ranked_hypotheses", [])
            hypotheses = []
            for h in raw_hypotheses:
                hypotheses.append(
                    HypothesisItem(
                        id=str(h.get("id", "H1")),
                        title=str(h.get("title", "Bottleneck Hypothesis")),
                        description=str(h.get("description", "")),
                        likelihood=str(h.get("likelihood", "High")),
                        evidence=str(h.get("evidence", "Telemetry observation"))
                    )
                )

            return StructuredDiagnosisOutput(
                summary=synthesis.get("summary", "Performance optimization patch"),
                observed_symptoms=critic.get("observed_symptoms", ["Elevated latency under load"]),
                ranked_hypotheses=hypotheses,
                supporting_measurements=benchmark_metrics,
                supporting_code_locations=[],
                confidence_score=float(critic.get("confidence_score", 0.85)),
                uncertainty_notes=critic.get("uncertainty_notes", ""),
                proposed_patch_diff=synthesis.get("proposed_patch_diff", ""),
                affected_files=synthesis.get("affected_files", []),
                expected_benefits=synthesis.get("expected_benefits", "Estimated latency reduction"),
                potential_risks=critic.get("potential_risks", []),
                required_regression_tests=critic.get("required_regression_tests", []),
                verification_criteria=critic.get("verification_criteria", ["Latency improvement verified empirically"])
            )
        except Exception as e:
            logger.error(f"Multi-agent synthesis pipeline encountered error: {e}")
            raise LLMServiceError(f"Multi-agent diagnosis failed: {str(e)}")
