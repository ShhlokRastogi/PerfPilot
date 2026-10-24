from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

class BenchmarkMetricResponse(BaseModel):
    id: int
    run_id: str
    phase: str
    p50_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput_rps: float
    total_requests: int
    failed_requests: int
    error_rate_pct: float
    duration_sec: float
    lcp_ms: Optional[float] = None
    ttfb_ms: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
