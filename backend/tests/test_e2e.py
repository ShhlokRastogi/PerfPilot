import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.database import init_db
from backend.app.models.run import RunStatus, Verdict

@pytest_asyncio.fixture(autouse=True)
async def prepare():
    await init_db()

@pytest.mark.asyncio
async def test_full_autonomous_optimization_lifecycle_e2e(monkeypatch):
    """
    End-to-End verification of the entire PerfPilot optimization lifecycle:
    Ingestion -> Baseline Benchmark -> AI Diagnosis -> Approval Gate ->
    Disposable Sandbox Execution -> Regression Testing -> Candidate Benchmark ->
    Deterministic Verification -> Final Auditable Report
    """
    # Mock benchmark service to provide deterministic benchmark metrics without external dependencies
    async def mock_run_benchmark(cls, run_id: str, phase: str, target_url: str, workload_config: dict):
        if phase == "baseline":
            return {
                "phase": "baseline",
                "run_id": run_id,
                "p50_latency_ms": 180.0,
                "p90_latency_ms": 380.0,
                "p95_latency_ms": 420.0,
                "p99_latency_ms": 580.0,
                "avg_latency_ms": 200.0,
                "min_latency_ms": 100.0,
                "max_latency_ms": 650.0,
                "throughput_rps": 22.5,
                "error_rate_pct": 0.0,
                "total_requests": 200,
                "failed_requests": 0,
                "duration_sec": 2.0,
                "raw_data": {}
            }
        else:
            return {
                "phase": "candidate",
                "run_id": run_id,
                "p50_latency_ms": 15.0,
                "p90_latency_ms": 30.0,
                "p95_latency_ms": 35.0,
                "p99_latency_ms": 55.0,
                "avg_latency_ms": 18.0,
                "min_latency_ms": 10.0,
                "max_latency_ms": 70.0,
                "throughput_rps": 185.0,
                "error_rate_pct": 0.0,
                "total_requests": 1500,
                "failed_requests": 0,
                "duration_sec": 2.0,
                "raw_data": {}
            }

    monkeypatch.setattr(
        "backend.app.services.benchmark_service.BenchmarkService.run_benchmark",
        classmethod(mock_run_benchmark)
    )

    # Mock candidate sandbox launcher to avoid conflicting live socket binding
    class MockCandidateEnv:
        candidate_url = "http://127.0.0.1:8002/api/products"
        health_url = "http://127.0.0.1:8002/health"
        def stop(self):
            pass

    async def mock_launch_candidate(cls, candidate_dir: str, **kwargs):
        return MockCandidateEnv()

    monkeypatch.setattr(
        "backend.app.services.sandbox_service.SandboxService.launch_candidate_service",
        classmethod(mock_launch_candidate)
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Step 1: Create new performance analysis run
        create_payload = {
            "target_type": "api",
            "target_url": "http://127.0.0.1:8001/api/products",
            "repo_path": "demo-app",
            "objectives": {
                "p95_latency_ms": 250.0,
                "min_speedup_factor": 1.5,
                "max_error_rate_pct": 1.0
            },
            "workload_config": {
                "vus": 4,
                "duration_sec": 2
            }
        }

        resp = await ac.post("/api/runs", json=create_payload)
        assert resp.status_code == 201
        run_data = resp.json()
        run_id = run_data["id"]
        assert run_data["status"] == "created"

        # Step 2: Poll until run reaches AWAITING_APPROVAL
        status_reached = None
        for _ in range(80):
            st_res = await ac.get(f"/api/runs/{run_id}/status")
            assert st_res.status_code == 200
            current_status = st_res.json()["status"]
            if current_status == "awaiting_approval":
                status_reached = current_status
                break
            if current_status == "failed":
                pytest.fail(f"Run unexpectedly failed during baseline pipeline: {st_res.json().get('failure_reason')}")
            await asyncio.sleep(0.5)

        assert status_reached == "awaiting_approval", f"Expected awaiting_approval, got {current_status}"

        # Step 3: Inspect baseline metrics
        metrics_res = await ac.get(f"/api/runs/{run_id}/metrics")
        assert metrics_res.status_code == 200
        metrics = metrics_res.json()
        assert len(metrics) >= 1
        baseline_metric = next(m for m in metrics if m["phase"] == "baseline")
        assert baseline_metric["p95_latency_ms"] > 0
        assert baseline_metric["throughput_rps"] > 0
        assert baseline_metric["total_requests"] > 0

        # Step 4: Inspect diagnosis and exact patch hash
        diag_res = await ac.get(f"/api/runs/{run_id}/diagnosis")
        assert diag_res.status_code == 200
        diag = diag_res.json()
        assert len(diag["summary"]) > 0
        assert len(diag["patch_hash"]) == 64
        assert len(diag["ranked_hypotheses"]) > 0
        assert len(diag["supporting_code_locations"]) > 0
        patch_hash = diag["patch_hash"]

        # Step 5: Submit Approval Decision (Approval Gate)
        approval_res = await ac.post(f"/api/runs/{run_id}/approval", json={
            "patch_hash": patch_hash,
            "decision": "approved",
            "reviewed_by": "sr_performance_engineer"
        })
        assert approval_res.status_code == 200
        assert approval_res.json()["status"] == "approved"

        # Step 6: Poll candidate execution to completion
        final_status = None
        for _ in range(50):
            st_res = await ac.get(f"/api/runs/{run_id}/status")
            current_status = st_res.json()["status"]
            if current_status in ["completed", "failed"]:
                final_status = current_status
                break
            await asyncio.sleep(0.5)

        assert final_status == "completed", f"Expected completed, got {final_status}"

        # Step 7: Inspect candidate metrics and verified improvement
        metrics_after = (await ac.get(f"/api/runs/{run_id}/metrics")).json()
        candidate_metric = next(m for m in metrics_after if m["phase"] == "candidate")
        assert candidate_metric["p95_latency_ms"] < baseline_metric["p95_latency_ms"]
        assert candidate_metric["error_rate_pct"] <= 1.0

        # Step 8: Inspect final deterministic report
        rep_res = await ac.get(f"/api/runs/{run_id}/report")
        assert rep_res.status_code == 200
        report = rep_res.json()
        assert report["verdict"] in [Verdict.VERIFIED_IMPROVEMENT.value, Verdict.NO_IMPROVEMENT.value]
        assert report["regression_passed"] is True
        assert report["p95_improvement_pct"] > 0.0

        # Step 9: Inspect complete audit trail
        audit_res = await ac.get(f"/api/runs/{run_id}/audit")
        assert audit_res.status_code == 200
        events = audit_res.json()
        event_types = [e["event_type"] for e in events]
        assert "STATE_TRANSITION" in event_types
        assert any(e["to_state"] == "awaiting_approval" for e in events)
        assert any(e["to_state"] == "applying_patch" for e in events)
        assert any(e["to_state"] == "completed" for e in events)
