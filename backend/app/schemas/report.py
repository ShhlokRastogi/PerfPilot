from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime
from backend.app.models.run import Verdict

class ReportResponse(BaseModel):
    id: int
    run_id: str
    verdict: Verdict
    summary: str
    p95_baseline_ms: float
    p95_candidate_ms: float
    p95_improvement_pct: float
    throughput_baseline_rps: float
    throughput_candidate_rps: float
    throughput_improvement_pct: float
    regression_passed: bool
    objectives_met: bool
    is_conclusive: bool
    details: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
