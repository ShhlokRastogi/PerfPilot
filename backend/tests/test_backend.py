import pytest
import pytest_asyncio
import hashlib
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete
from backend.app.main import app
from backend.app.core.database import init_db, AsyncSessionLocal
from backend.app.models.run import Run, RunStatus, ApprovalStatus, Verdict, PatchApproval, DiagnosisModel
from backend.app.services.verification_service import VerificationService
from backend.app.services.approval_service import ApprovalService, ApprovalSecurityError
from backend.app.services.diagnosis_service import DiagnosisService
from backend.app.schemas.run import RunCreateRequest, PersonaConfig

@pytest_asyncio.fixture(autouse=True)
async def prepare_db():
    await init_db()
    yield

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "PerfPilot"

@pytest.mark.asyncio
async def test_input_validation_invalid_payload():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Missing required workload / malformed types
        resp = await ac.post("/api/runs", json={"target_type": 123, "objectives": "invalid_type"})
        assert resp.status_code in [400, 422]

@pytest.mark.asyncio
async def test_persona_config_validation():
    req = RunCreateRequest(
        target_type="api",
        target_url="http://localhost:3000",
        repo_path=".",
        personas=[
            PersonaConfig(role="heavy_workload", traffic_pct=70, path="/api/heavy"),
            PersonaConfig(role="standard_workload", traffic_pct=20, path="/api/standard", headers={"Authorization": "Bearer token"}),
            PersonaConfig(role="background_workload", traffic_pct=10, path="/api/background")
        ]
    )
    assert len(req.personas) == 3
    assert req.personas[0].role == "heavy_workload"
    assert req.personas[0].traffic_pct == 70
    assert req.personas[1].headers["Authorization"] == "Bearer token"

@pytest.mark.asyncio
async def test_deterministic_metric_calculations():
    # p95 drops from 400ms to 40ms -> 90% improvement
    p95_imp = VerificationService.calculate_percentage_change(400.0, 40.0, lower_is_better=True)
    assert p95_imp == 90.0

    # throughput rises from 20 to 100 rps -> 400% improvement
    rps_imp = VerificationService.calculate_percentage_change(20.0, 100.0, lower_is_better=False)
    assert rps_imp == 400.0

    # Evaluation with passing regression and objectives met
    baseline = {"p95_latency_ms": 500.0, "throughput_rps": 20.0}
    candidate = {"p95_latency_ms": 25.0, "throughput_rps": 120.0, "error_rate_pct": 0.0, "total_requests": 500}
    objectives = {"p95_latency_ms": 250.0, "min_speedup_factor": 2.0, "max_error_rate_pct": 1.0}

    verdict, summary, details = VerificationService.evaluate_results(
        baseline_metrics=baseline,
        candidate_metrics=candidate,
        objectives=objectives,
        regression_passed=True
    )
    assert verdict == Verdict.VERIFIED_IMPROVEMENT
    assert details["speedup_factor"] == 20.0
    assert details["objectives_met"] is True

@pytest.mark.asyncio
async def test_regression_failure_forces_rollback():
    baseline = {"p95_latency_ms": 500.0, "throughput_rps": 20.0}
    candidate = {"p95_latency_ms": 20.0, "throughput_rps": 200.0, "error_rate_pct": 0.0, "total_requests": 500}
    objectives = {"p95_latency_ms": 250.0}

    # If regression_passed is False, must FAIL regardless of performance
    verdict, summary, details = VerificationService.evaluate_results(
        baseline_metrics=baseline,
        candidate_metrics=candidate,
        objectives=objectives,
        regression_passed=False
    )
    assert verdict == Verdict.FAILED
    assert details["regression_passed"] is False

@pytest.mark.asyncio
async def test_patch_hash_computation_and_normalization():
    diff_crlf = "--- a/file.py\r\n+++ b/file.py\r\n@@ -1 +1 @@\r\n-old\r\n+new\r\n"
    diff_lf = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new\n"
    
    hash_crlf = DiagnosisService.compute_patch_hash(diff_crlf)
    hash_lf = DiagnosisService.compute_patch_hash(diff_lf)

    assert len(hash_crlf) == 64
    assert hash_crlf == hash_lf, "Normalized hash must be invariant across CRLF and LF line endings"

@pytest.mark.asyncio
async def test_rejection_prevents_patch_execution():
    test_run_id = f"test_{uuid.uuid4().hex[:12]}"
    sample_patch = "--- a/code.py\n+++ b/code.py\n@@ -1,1 +1,1 @@\n-pass\n+return True\n"
    expected_hash = DiagnosisService.compute_patch_hash(sample_patch)

    async with AsyncSessionLocal() as db:
        try:
            run = Run(
                id=test_run_id,
                status=RunStatus.AWAITING_APPROVAL.value,
                target_type="api",
                target_url="http://127.0.0.1:3000",
                repo_path=".",
                objectives={"p95_latency_ms": 200},
                workload_config={"vus": 2, "duration_sec": 1}
            )
            db.add(run)

            approval = PatchApproval(
                run_id=test_run_id,
                patch_hash=expected_hash,
                status=ApprovalStatus.PENDING.value
            )
            db.add(approval)
            await db.commit()

            # Execute rejection directly via ApprovalService
            appr = await ApprovalService.process_decision(
                db=db,
                run_id=test_run_id,
                patch_hash=expected_hash,
                decision=ApprovalStatus.REJECTED,
                reviewed_by="qa_tester",
                decision_reason="High risk of lock contention"
            )
            assert appr.status == ApprovalStatus.REJECTED.value
            assert run.status == RunStatus.REJECTED.value
        finally:
            # Clean up test row so database stays clean
            await db.execute(delete(PatchApproval).where(PatchApproval.run_id == test_run_id))
            await db.execute(delete(Run).where(Run.id == test_run_id))
            await db.commit()

@pytest.mark.asyncio
async def test_patch_hash_mismatch_security_gate():
    test_run_id = f"test_{uuid.uuid4().hex[:12]}"
    sample_patch = "--- a/code.py\n+++ b/code.py\n@@ -1,1 +1,1 @@\n-pass\n+return True\n"
    expected_hash = DiagnosisService.compute_patch_hash(sample_patch)

    async with AsyncSessionLocal() as db:
        try:
            run = Run(
                id=test_run_id,
                status=RunStatus.AWAITING_APPROVAL.value,
                target_type="api",
                target_url="http://127.0.0.1:3000",
                repo_path=".",
                objectives={"p95_latency_ms": 200},
                workload_config={"vus": 2, "duration_sec": 1}
            )
            db.add(run)

            approval = PatchApproval(
                run_id=test_run_id,
                patch_hash=expected_hash,
                status=ApprovalStatus.PENDING.value
            )
            db.add(approval)
            await db.commit()

            # Attempt approval with tampered/wrong patch hash
            fake_hash = "0000000000000000000000000000000000000000000000000000000000000000"
            with pytest.raises(ApprovalSecurityError) as exc_info:
                await ApprovalService.process_decision(
                    db=db,
                    run_id=test_run_id,
                    patch_hash=fake_hash,
                    decision=ApprovalStatus.APPROVED,
                    reviewed_by="attacker"
                )
            assert exc_info.value.code == "HASH_MISMATCH"
            assert "Patch hash mismatch" in exc_info.value.message
        finally:
            # Clean up test row so database stays clean
            await db.execute(delete(PatchApproval).where(PatchApproval.run_id == test_run_id))
            await db.execute(delete(Run).where(Run.id == test_run_id))
            await db.commit()
