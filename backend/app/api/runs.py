import os
import shutil
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.run import (
    Run, AuditEvent, BenchmarkMetric, DiagnosisModel, PatchApproval, RunReport, ApprovalStatus, EvidenceModel
)
from backend.app.schemas.run import RunCreateRequest, RunResponse, AuditEventResponse
from backend.app.schemas.benchmark import BenchmarkMetricResponse
from backend.app.schemas.diagnosis import DiagnosisResponse
from backend.app.schemas.approval import ApprovalDecisionRequest, PatchApprovalResponse
from backend.app.schemas.report import ReportResponse
from backend.app.evidence.schema import EvidenceRecord
from backend.app.services.orchestration_service import OrchestrationService
from backend.app.services.approval_service import ApprovalSecurityError
from backend.app.services.sandbox_service import get_sandbox_steps

router = APIRouter(prefix="/api/runs", tags=["runs"])

@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(req: RunCreateRequest):
    """
    Creates a new performance optimization analysis run and triggers the baseline workflow.
    """
    workload_cfg = dict(req.workload_config)
    if req.personas:
        workload_cfg["personas"] = [p.model_dump() for p in req.personas]

    run = await OrchestrationService.create_and_start_run(
        target_type=req.target_type,
        target_url=req.target_url,
        repo_path=req.repo_path,
        objectives=req.objectives,
        workload_config=workload_cfg
    )
    return run

@router.get("", response_model=List[RunResponse])
async def list_runs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """
    Lists recent analysis runs ordered by creation date descending.
    """
    stmt = select(Run).order_by(desc(Run.created_at)).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.delete("", status_code=status.HTTP_200_OK)
async def clear_all_runs(db: AsyncSession = Depends(get_db)):
    """
    Clears all analysis runs, audit events, benchmark metrics, diagnoses, and reports.
    """
    await db.execute(delete(RunReport))
    await db.execute(delete(PatchApproval))
    await db.execute(delete(DiagnosisModel))
    await db.execute(delete(EvidenceModel))
    await db.execute(delete(BenchmarkMetric))
    await db.execute(delete(AuditEvent))
    await db.execute(delete(Run))
    await db.commit()

    # Clean artifacts directory (preserve .gitkeep)
    if os.path.exists(settings.ARTIFACTS_DIR):
        for item in os.listdir(settings.ARTIFACTS_DIR):
            if item != ".gitkeep":
                p = os.path.join(settings.ARTIFACTS_DIR, item)
                try:
                    if os.path.isdir(p):
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        os.remove(p)
                except Exception:
                    pass

    return {"message": "All recent runs and artifacts cleared successfully"}

@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.get("/{run_id}/status")
async def get_run_status(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "id": run.id,
        "status": run.status,
        "failure_reason": run.failure_reason,
        "updated_at": run.updated_at
    }

@router.get("/{run_id}/metrics", response_model=List[BenchmarkMetricResponse])
async def get_run_metrics(run_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(BenchmarkMetric).where(BenchmarkMetric.run_id == run_id).order_by(BenchmarkMetric.created_at)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{run_id}/diagnosis", response_model=DiagnosisResponse)
async def get_run_diagnosis(run_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(DiagnosisModel).where(DiagnosisModel.run_id == run_id)
    res = await db.execute(stmt)
    diag = res.scalar_one_or_none()
    if not diag:
        raise HTTPException(status_code=404, detail="Diagnosis not yet available for this run")
    return diag

@router.post("/{run_id}/approval", response_model=PatchApprovalResponse)
async def submit_approval_decision(
    run_id: str,
    req: ApprovalDecisionRequest
):
    """
    Explicit human approval gate:
    Requires exact matching patch_hash. Client CANNOT bypass this gate.
    """
    try:
        approval = await OrchestrationService.handle_approval_decision(
            run_id=run_id,
            patch_hash=req.patch_hash,
            decision=req.decision,
            reviewed_by=req.reviewed_by,
            decision_reason=req.decision_reason
        )
        return approval
    except ApprovalSecurityError as e:
        if e.code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=e.message)
        elif e.code == "HASH_MISMATCH":
            raise HTTPException(status_code=409, detail=e.message)
        elif e.code == "INVALID_STATE":
            raise HTTPException(status_code=400, detail=e.message)
        else:
            raise HTTPException(status_code=403, detail=e.message)

@router.get("/{run_id}/report", response_model=ReportResponse)
async def get_run_report(run_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(RunReport).where(RunReport.run_id == run_id)
    res = await db.execute(stmt)
    rep = res.scalar_one_or_none()
    if not rep:
        raise HTTPException(status_code=404, detail="Report not yet generated for this run")
    return rep

@router.get("/{run_id}/audit", response_model=List[AuditEventResponse])
async def get_run_audit_events(run_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AuditEvent).where(AuditEvent.run_id == run_id).order_by(AuditEvent.timestamp)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{run_id}/sandbox-steps")
async def get_run_sandbox_steps(run_id: str):
    """
    Returns live step-by-step sandbox execution status, durations, and console output.
    """
    return get_sandbox_steps(run_id)

@router.get("/{run_id}/evidence", response_model=List[EvidenceRecord])
async def get_run_evidence(run_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns all empirical EvidenceRecords collected by diagnostic workers and AST indexers for this run.
    """
    stmt = select(EvidenceModel).where(EvidenceModel.run_id == run_id).order_by(EvidenceModel.timestamp)
    res = await db.execute(stmt)
    return res.scalars().all()
