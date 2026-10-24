import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.run import Run, RunStatus, PatchApproval, ApprovalStatus, AuditEvent, DiagnosisModel
from backend.app.core.state_machine import transition_run_state, InvalidStateTransitionError

class ApprovalSecurityError(Exception):
    def __init__(self, message: str, code: str = "FORBIDDEN"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class ApprovalService:
    @classmethod
    async def process_decision(
        cls,
        db: AsyncSession,
        run_id: str,
        patch_hash: str,
        decision: ApprovalStatus,
        reviewed_by: Optional[str] = "engineer",
        decision_reason: Optional[str] = None
    ) -> PatchApproval:
        """
        Validates the run state and exact cryptographic patch hash.
        Transitions state to APPLYING_PATCH (if approved) or REJECTED (if rejected).
        Enforces that no modified or unapproved patch can ever execute.
        """
        # Fetch Run
        run = await db.get(Run, run_id)
        if not run:
            raise ApprovalSecurityError(f"Run {run_id} not found", "NOT_FOUND")

        # Verify run is strictly in AWAITING_APPROVAL state
        if run.status != RunStatus.AWAITING_APPROVAL.value:
            raise ApprovalSecurityError(
                f"Run is in state '{run.status}', not '{RunStatus.AWAITING_APPROVAL.value}'. Approval can only be decided when awaiting approval.",
                "INVALID_STATE"
            )

        # Fetch PatchApproval record
        stmt = select(PatchApproval).where(PatchApproval.run_id == run_id)
        res = await db.execute(stmt)
        approval = res.scalar_one_or_none()

        if not approval:
            raise ApprovalSecurityError("No pending patch approval found for this run", "NO_APPROVAL_RECORD")

        # Verify EXACT patch hash match
        if approval.patch_hash.strip().lower() != patch_hash.strip().lower():
            # Tampering or out-of-sync patch detected!
            audit = AuditEvent(
                run_id=run.id,
                event_type="APPROVAL_HASH_MISMATCH",
                from_state=run.status,
                to_state=run.status,
                message="Approval rejected: submitted patch hash does not match diagnostic proposal",
                details={
                    "expected_hash": approval.patch_hash,
                    "submitted_hash": patch_hash,
                    "reviewed_by": reviewed_by
                }
            )
            db.add(audit)
            await db.commit()
            raise ApprovalSecurityError(
                f"Patch hash mismatch! Expected {approval.patch_hash}, received {patch_hash}. Any patch modification invalidates approval.",
                "HASH_MISMATCH"
            )

        # Record decision
        approval.status = decision.value
        approval.reviewed_by = reviewed_by
        approval.decision_reason = decision_reason
        approval.decided_at = datetime.utcnow()

        if decision == ApprovalStatus.REJECTED:
            # Transition to REJECTED terminal state
            await transition_run_state(
                db=db,
                run=run,
                target_status=RunStatus.REJECTED,
                message=f"Patch rejected by {reviewed_by}. Execution permanently halted.",
                details={"reason": decision_reason, "patch_hash": patch_hash}
            )
        elif decision == ApprovalStatus.APPROVED:
            # Transition to APPLYING_PATCH
            await transition_run_state(
                db=db,
                run=run,
                target_status=RunStatus.APPLYING_PATCH,
                message=f"Patch approved by {reviewed_by}. Proceeding to isolated sandbox execution.",
                details={"patch_hash": patch_hash}
            )

        await db.commit()
        await db.refresh(approval)
        return approval
