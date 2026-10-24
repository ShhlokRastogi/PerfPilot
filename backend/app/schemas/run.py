from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from backend.app.models.run import RunStatus, Verdict, ApprovalStatus

class PersonaConfig(BaseModel):
    role: str = Field(default="primary_workload", description="Dynamic workload identifier")
    traffic_pct: int = Field(default=100, description="Percentage of total workload allocated (1-100)")
    path: str = Field(default="", description="Endpoint path or query")
    headers: Dict[str, str] = Field(default_factory=dict, description="Optional request headers e.g. Authorization")

class RunCreateRequest(BaseModel):
    target_type: str = Field(default="api", description="Target type: api or web")
    repo_path: str = Field(default=".", description="Relative or absolute path to target codebase")
    endpoint_path: str = Field(default="/", description="Endpoint route path to benchmark (e.g. / or /api/products)")
    target_url: Optional[str] = Field(default="", description="Optional external URL. If omitted or empty, PerfPilot auto-launches the repo in an isolated sandbox")
    personas: List[PersonaConfig] = Field(
        default_factory=list,
        description="Dynamic workload configuration"
    )
    objectives: Dict[str, Any] = Field(
        default_factory=lambda: {
            "p95_latency_ms": 250.0,
            "min_speedup_factor": 1.5,
            "max_error_rate_pct": 1.0
        },
        description="Target performance objectives"
    )
    workload_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "vus": 10,
            "duration_sec": 10,
            "concurrency": 10
        },
        description="Load test parameters"
    )

class AuditEventResponse(BaseModel):
    id: int
    run_id: str
    event_type: str
    from_state: Optional[str]
    to_state: Optional[str]
    message: str
    details: Dict[str, Any]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class RunResponse(BaseModel):
    id: str
    status: RunStatus
    target_type: str
    target_url: str
    repo_path: str
    objectives: Dict[str, Any]
    workload_config: Dict[str, Any]
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
