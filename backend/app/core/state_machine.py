from typing import Dict, Set, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.run import Run, RunStatus, AuditEvent

# Valid state transitions graph
VALID_TRANSITIONS: Dict[RunStatus, Set[RunStatus]] = {
    RunStatus.CREATED: {RunStatus.VALIDATING, RunStatus.FAILED},
    RunStatus.VALIDATING: {RunStatus.PREPARING_BASELINE, RunStatus.FAILED},
    RunStatus.PREPARING_BASELINE: {RunStatus.BENCHMARKING_BASELINE, RunStatus.FAILED},
    RunStatus.BENCHMARKING_BASELINE: {RunStatus.DIAGNOSING, RunStatus.COMPLETED, RunStatus.FAILED},
    RunStatus.DIAGNOSING: {RunStatus.AWAITING_APPROVAL, RunStatus.COMPLETED, RunStatus.FAILED},
    RunStatus.AWAITING_APPROVAL: {RunStatus.APPLYING_PATCH, RunStatus.REJECTED, RunStatus.FAILED},
    RunStatus.APPLYING_PATCH: {RunStatus.TESTING_CANDIDATE, RunStatus.FAILED},
    RunStatus.TESTING_CANDIDATE: {RunStatus.BENCHMARKING_CANDIDATE, RunStatus.FAILED},
    RunStatus.BENCHMARKING_CANDIDATE: {RunStatus.VERIFYING, RunStatus.FAILED},
    RunStatus.VERIFYING: {RunStatus.COMPLETED, RunStatus.FAILED},
    RunStatus.REJECTED: set(),  # Terminal
    RunStatus.COMPLETED: set(), # Terminal
    RunStatus.FAILED: set(),    # Terminal
}

class InvalidStateTransitionError(Exception):
    def __init__(self, current_status: RunStatus, target_status: RunStatus, reason: Optional[str] = None):
        self.current_status = current_status
        self.target_status = target_status
        self.reason = reason or f"Cannot transition from {current_status.value} to {target_status.value}"
        super().__init__(self.reason)

async def transition_run_state(
    db: AsyncSession,
    run: Run,
    target_status: RunStatus,
    message: str,
    details: Optional[Dict] = None
) -> Run:
    """
    Validates and executes a state transition on a Run, recording an AuditEvent.
    Raises InvalidStateTransitionError if the transition is disallowed.
    """
    current_status = RunStatus(run.status)
    allowed = VALID_TRANSITIONS.get(current_status, set())
    
    if target_status not in allowed:
        # Record failed transition attempt in audit log
        audit = AuditEvent(
            run_id=run.id,
            event_type="ILLEGAL_STATE_TRANSITION_ATTEMPT",
            from_state=current_status.value,
            to_state=target_status.value,
            message=f"Blocked invalid transition to {target_status.value}",
            details={"allowed_targets": [s.value for s in allowed]}
        )
        db.add(audit)
        await db.commit()
        raise InvalidStateTransitionError(current_status, target_status)

    from_state = run.status
    run.status = target_status.value
    run.updated_at = datetime.utcnow()
    
    audit = AuditEvent(
        run_id=run.id,
        event_type="STATE_TRANSITION",
        from_state=from_state,
        to_state=target_status.value,
        message=message,
        details=details or {}
    )
    db.add(audit)
    await db.commit()
    await db.refresh(run)
    return run
