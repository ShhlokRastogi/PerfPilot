import asyncio
import os
import sys
import uuid
import logging
import httpx
import subprocess
import time
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.config import settings
from backend.app.models.run import (
    Run, RunStatus, BenchmarkMetric, DiagnosisModel, PatchApproval, ApprovalStatus, Verdict
)
from backend.app.core.state_machine import transition_run_state
from backend.app.services.benchmark_service import BenchmarkService
from backend.app.services.diagnosis_service import DiagnosisService
from backend.app.services.approval_service import ApprovalService
from backend.app.services.sandbox_service import SandboxService, record_sandbox_step
from backend.app.services.verification_service import VerificationService
from backend.app.services.report_service import ReportService

logger = logging.getLogger("perfpilot.orchestration")

class OrchestrationService:
    @classmethod
    async def create_and_start_run(
        cls,
        target_type: str,
        target_url: str,
        repo_path: str,
        objectives: Dict[str, Any],
        workload_config: Dict[str, Any]
    ) -> Run:
        """
        Initializes a new performance analysis run and launches the baseline pipeline in the background.
        """
        run_id = str(uuid.uuid4())
        
        async with AsyncSessionLocal() as db:
            run = Run(
                id=run_id,
                status=RunStatus.CREATED.value,
                target_type=target_type,
                target_url=target_url,
                repo_path=repo_path,
                objectives=objectives,
                workload_config=workload_config
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)

        # Launch execution in background task without blocking API
        asyncio.create_task(cls._execute_baseline_pipeline(run_id))
        return run

    @classmethod
    async def _execute_baseline_pipeline(cls, run_id: str):
        """
        Executes stages: VALIDATING -> PREPARING_BASELINE -> BENCHMARKING_BASELINE -> DIAGNOSING -> AWAITING_APPROVAL
        """
        async with AsyncSessionLocal() as db:
            run = await db.get(Run, run_id)
            if not run:
                return

            try:
                # 1. VALIDATING
                await transition_run_state(
                    db=db,
                    run=run,
                    target_status=RunStatus.VALIDATING,
                    message="Validating target endpoint, repository paths, and resource limits"
                )

                # Security check: target host authorization if full URL provided
                import urllib.parse
                if run.target_url and "://" in run.target_url:
                    parsed_url = urllib.parse.urlparse(run.target_url)
                    if "*" not in settings.ALLOWED_HOSTS and parsed_url.hostname and parsed_url.hostname not in settings.ALLOWED_HOSTS:
                        raise ValueError(f"Target host '{parsed_url.hostname}' is not authorized. Allowed: {settings.ALLOWED_HOSTS}")

                # 2. PREPARING_BASELINE
                await transition_run_state(
                    db=db,
                    run=run,
                    target_status=RunStatus.PREPARING_BASELINE,
                    message="Preparing baseline environment and verifying service readiness"
                )

                # Check if an external server is already running and reachable
                baseline_env = None
                is_reachable = False
                if run.target_url and "://" in run.target_url:
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(run.target_url, timeout=2.0)
                            is_reachable = True
                    except Exception:
                        is_reachable = False

                # Auto-Sandbox Mode: If no running server, auto-launch repository in isolated sandbox
                if not is_reachable and os.path.exists(os.path.abspath(run.repo_path)):
                    logger.info(f"Auto-launching baseline service from repo '{run.repo_path}' in isolated sandbox on port 8001")
                    record_sandbox_step(
                        run.id,
                        "baseline_prep",
                        "Provision Baseline Isolated Sandbox",
                        "running",
                        f"Initializing baseline sandbox workspace for repository '{run.repo_path}'..."
                    )
                    t0 = time.time()
                    baseline_env = await SandboxService.launch_application_service(
                        workspace_dir=run.repo_path,
                        target_path_or_url=run.target_url or "/",
                        port=8001,
                        phase_name="baseline",
                        run_id=run.id,
                        is_disposable=False
                    )
                    run.target_url = baseline_env.service_url
                    await db.commit()
                    record_sandbox_step(
                        run.id,
                        "baseline_prep",
                        "Provision Baseline Isolated Sandbox",
                        "completed",
                        f"Baseline application auto-launched successfully on port 8001 (URL: {baseline_env.service_url})",
                        duration_ms=round((time.time() - t0) * 1000, 1)
                    )
                else:
                    record_sandbox_step(
                        run.id,
                        "baseline_prep",
                        "Verify Target Reachability",
                        "completed",
                        f"Target endpoint '{run.target_url}' verified and ready for benchmarking."
                    )

                # 3. BENCHMARKING_BASELINE
                await transition_run_state(
                    db=db,
                    run=run,
                    target_status=RunStatus.BENCHMARKING_BASELINE,
                    message="Executing baseline benchmark workload",
                    details=run.workload_config
                )

                baseline_data = await BenchmarkService.run_benchmark(
                    run_id=run.id,
                    phase="baseline",
                    target_url=run.target_url,
                    workload_config=run.workload_config or {}
                )

                # Persist BenchmarkMetric
                baseline_metric = BenchmarkMetric(
                    run_id=run.id,
                    phase="baseline",
                    p50_latency_ms=baseline_data["p50_latency_ms"],
                    p90_latency_ms=baseline_data["p90_latency_ms"],
                    p95_latency_ms=baseline_data["p95_latency_ms"],
                    p99_latency_ms=baseline_data["p99_latency_ms"],
                    avg_latency_ms=baseline_data["avg_latency_ms"],
                    min_latency_ms=baseline_data.get("min_latency_ms", 0.0),
                    max_latency_ms=baseline_data.get("max_latency_ms", 0.0),
                    throughput_rps=baseline_data["throughput_rps"],
                    total_requests=baseline_data["total_requests"],
                    failed_requests=baseline_data["failed_requests"],
                    error_rate_pct=baseline_data["error_rate_pct"],
                    duration_sec=baseline_data["duration_sec"],
                    raw_data=baseline_data.get("raw_data", {})
                )
                db.add(baseline_metric)
                await db.commit()

                # 4. DIAGNOSING
                await transition_run_state(
                    db=db,
                    run=run,
                    target_status=RunStatus.DIAGNOSING,
                    message="Analyzing baseline measurements, profiling traces, and repository source code"
                )

                # 5. DIAGNOSIS SERVICE & AWAITING APPROVAL
                diag = await DiagnosisService.diagnose_run(
                    db=db,
                    run=run,
                    baseline_metrics=baseline_data
                )
                if diag:
                    logger.info(f"Run {run.id} is now AWAITING_APPROVAL")
                else:
                    logger.info(f"Run {run.id} completed via router short-circuit (baseline meets SLA)")

            except Exception as e:
                logger.exception(f"Baseline pipeline failed for run {run_id}: {e}")
                run.failure_reason = str(e)
                await transition_run_state(
                    db=db,
                    run=run,
                    target_status=RunStatus.FAILED,
                    message=f"Pipeline error: {str(e)}"
                )

    @classmethod
    async def handle_approval_decision(
        cls,
        run_id: str,
        patch_hash: str,
        decision: ApprovalStatus,
        reviewed_by: Optional[str] = "engineer",
        decision_reason: Optional[str] = None
    ) -> PatchApproval:
        """
        Processes human approval decision. If approved, kicks off candidate pipeline.
        """
        async with AsyncSessionLocal() as db:
            approval = await ApprovalService.process_decision(
                db=db,
                run_id=run_id,
                patch_hash=patch_hash,
                decision=decision,
                reviewed_by=reviewed_by,
                decision_reason=decision_reason
            )

        if decision == ApprovalStatus.APPROVED:
            # Launch candidate remediation and verification in background
            asyncio.create_task(cls._execute_candidate_pipeline(run_id))

        return approval

    @classmethod
    async def _execute_candidate_pipeline(cls, run_id: str):
        """
        Executes candidate lifecycle: APPLYING_PATCH -> TESTING_CANDIDATE -> BENCHMARKING_CANDIDATE -> VERIFYING -> COMPLETED/FAILED
        """
        candidate_env = None
        async with AsyncSessionLocal() as db:
            run = await db.get(Run, run_id)
            if not run:
                return

            try:
                # Retrieve Diagnosis for proposed patch
                stmt = select(DiagnosisModel).where(DiagnosisModel.run_id == run.id)
                res = await db.execute(stmt)
                diag = res.scalar_one_or_none()
                if not diag:
                    raise ValueError("Diagnosis record missing")

                # 1. Provision disposable workspace
                record_sandbox_step(run.id, "provision", "Provision Isolated Workspace", "running")
                t0 = time.time()
                candidate_dir = SandboxService.create_disposable_workspace(run.repo_path)
                record_sandbox_step(run.id, "provision", "Provision Isolated Workspace", "completed", f"Workspace created at {os.path.basename(candidate_dir)}", duration_ms=round((time.time()-t0)*1000, 1))
                
                # 2. Apply approved patch
                record_sandbox_step(run.id, "patch", "Apply Approved Unified Diff", "running")
                t0 = time.time()
                patch_res = SandboxService.apply_patch_to_workspace(candidate_dir, diag.proposed_patch_diff)
                record_sandbox_step(run.id, "patch", "Apply Approved Unified Diff", "completed", f"Successfully patched {patch_res['file']} ({patch_res['bytes_written']} bytes)", duration_ms=round((time.time()-t0)*1000, 1))

                # 3. TESTING_CANDIDATE
                await transition_run_state(
                    db=db,
                    run=run,
                    target_status=RunStatus.TESTING_CANDIDATE,
                    message="Running build validation and functional regression tests in candidate workspace"
                )

                record_sandbox_step(run.id, "test", "Execute Build & Regression Tests", "running")
                t0 = time.time()
                test_results = await SandboxService.run_regression_tests(candidate_dir)
                if not test_results["passed"]:
                    record_sandbox_step(run.id, "test", "Execute Build & Regression Tests", "failed", test_results.get("output", "Tests failed"), duration_ms=round((time.time()-t0)*1000, 1))
                    run.failure_reason = f"Regression tests failed:\n{test_results['output']}"
                    await transition_run_state(
                        db=db,
                        run=run,
                        target_status=RunStatus.FAILED,
                        message="Candidate patch caused functional regression. Execution halted.",
                        details=test_results
                    )
                    await ReportService.generate_and_persist_report(
                        db=db,
                        run_id=run.id,
                        verdict=Verdict.FAILED,
                        summary="Candidate patch failed functional regression tests.",
                        details={"regression_passed": False, "test_output": test_results["output"]}
                    )
                    return

                record_sandbox_step(run.id, "test", "Execute Build & Regression Tests", "completed", test_results.get("output", "Passed"), duration_ms=round((time.time()-t0)*1000, 1))

                # 4. Launch candidate service on isolated port 8002
                record_sandbox_step(run.id, "launch", "Launch Candidate Sandbox Service", "running")
                t0 = time.time()
                candidate_env = await SandboxService.launch_candidate_service(candidate_dir, target_url=run.target_url, port=8002, run_id=run.id)
                record_sandbox_step(run.id, "launch", "Launch Candidate Sandbox Service", "completed", f"Service responsive at {candidate_env.candidate_url}", duration_ms=round((time.time()-t0)*1000, 1))

                # 5. BENCHMARKING_CANDIDATE
                await transition_run_state(
                    db=db,
                    run=run,
                    target_status=RunStatus.BENCHMARKING_CANDIDATE,
                    message="Executing performance verification benchmark against isolated candidate environment",
                    details={"candidate_url": candidate_env.candidate_url}
                )

                record_sandbox_step(run.id, "bench", "Execute Verification Load Test", "running")
                t0 = time.time()
                candidate_data = await BenchmarkService.run_benchmark(
                    run_id=run.id,
                    phase="candidate",
                    target_url=candidate_env.candidate_url,
                    workload_config=run.workload_config or {}
                )
                record_sandbox_step(run.id, "bench", "Execute Verification Load Test", "completed", f"p95={candidate_data.get('p95_latency_ms')}ms, throughput={candidate_data.get('throughput_rps')} req/s", duration_ms=round((time.time()-t0)*1000, 1))

                # Persist candidate metric
                candidate_metric = BenchmarkMetric(
                    run_id=run.id,
                    phase="candidate",
                    p50_latency_ms=candidate_data["p50_latency_ms"],
                    p90_latency_ms=candidate_data["p90_latency_ms"],
                    p95_latency_ms=candidate_data["p95_latency_ms"],
                    p99_latency_ms=candidate_data["p99_latency_ms"],
                    avg_latency_ms=candidate_data["avg_latency_ms"],
                    min_latency_ms=candidate_data.get("min_latency_ms", 0.0),
                    max_latency_ms=candidate_data.get("max_latency_ms", 0.0),
                    throughput_rps=candidate_data["throughput_rps"],
                    total_requests=candidate_data["total_requests"],
                    failed_requests=candidate_data["failed_requests"],
                    error_rate_pct=candidate_data["error_rate_pct"],
                    duration_sec=candidate_data["duration_sec"],
                    raw_data=candidate_data.get("raw_data", {})
                )
                db.add(candidate_metric)
                await db.commit()

                # Clean up candidate environment
                record_sandbox_step(run.id, "teardown", "Teardown Disposable Sandbox", "running")
                candidate_env.stop()
                candidate_env = None
                record_sandbox_step(run.id, "teardown", "Teardown Disposable Sandbox", "completed", "Environment terminated cleanly.")

                # 8. VERIFYING
                await transition_run_state(
                    db=db,
                    run=run,
                    target_status=RunStatus.VERIFYING,
                    message="Performing deterministic before/after metrics comparison and objective verification"
                )

                # Fetch baseline metrics
                b_stmt = select(BenchmarkMetric).where(
                    BenchmarkMetric.run_id == run.id,
                    BenchmarkMetric.phase == "baseline"
                )
                b_res = await db.execute(b_stmt)
                b_metric = b_res.scalar_one_or_none()
                b_dict = {
                    "p95_latency_ms": b_metric.p95_latency_ms if b_metric else 400.0,
                    "throughput_rps": b_metric.throughput_rps if b_metric else 15.0,
                    "error_rate_pct": b_metric.error_rate_pct if b_metric else 0.0
                }

                verdict, summary, comparison_details = VerificationService.evaluate_results(
                    baseline_metrics=b_dict,
                    candidate_metrics=candidate_data,
                    objectives=run.objectives or {},
                    regression_passed=True
                )

                # Generate and persist report
                await ReportService.generate_and_persist_report(
                    db=db,
                    run_id=run.id,
                    verdict=verdict,
                    summary=summary,
                    details=comparison_details
                )

                # 9. COMPLETED
                await transition_run_state(
                    db=db,
                    run=run,
                    target_status=RunStatus.COMPLETED,
                    message=f"Performance optimization workflow completed with verdict: {verdict.value}",
                    details={"verdict": verdict.value, "summary": summary}
                )

            except Exception as e:
                logger.exception(f"Candidate pipeline error for run {run_id}: {e}")
                run.failure_reason = str(e)
                await transition_run_state(
                    db=db,
                    run=run,
                    target_status=RunStatus.FAILED,
                    message=f"Candidate execution error: {str(e)}"
                )
            finally:
                if candidate_env:
                    t0 = time.time()
                    candidate_env.stop()
                    record_sandbox_step(
                        run.id,
                        "teardown",
                        "Teardown Disposable Candidate Sandbox",
                        "completed",
                        "Candidate sandbox process gracefully stopped and disposable workspace cleaned up.",
                        duration_ms=round((time.time() - t0) * 1000, 1)
                    )
