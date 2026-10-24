from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from backend.app.models.run import ApprovalStatus

class ApprovalDecisionRequest(BaseModel):
    patch_hash: str = Field(description="Exact SHA-256 hash of the proposed patch diff")
    decision: ApprovalStatus = Field(description="Must be 'approved' or 'rejected'")
    reviewed_by: Optional[str] = Field(default="engineer", description="Name/ID of reviewer")
    decision_reason: Optional[str] = Field(default=None, description="Optional notes or reason for rejection")

class PatchApprovalResponse(BaseModel):
    id: int
    run_id: str
    status: ApprovalStatus
    patch_hash: str
    reviewed_by: Optional[str] = None
    decision_reason: Optional[str] = None
    decided_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
