from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid

class EvidenceRecord(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Globally unique evidence record ID")
    run_id: str = Field(description="Run ID associated with this piece of evidence")
    finding_id: Optional[str] = Field(default=None, description="Optional finding ID or hypothesis ID")
    category: str = Field(description="Diagnostic category: backend, database, frontend, repository, or critic")
    observation: str = Field(description="Objective factual observation without model-generated embellishment")
    measured_values: Dict[str, Any] = Field(default_factory=dict, description="Empirical measured values and metrics")
    unit: Optional[str] = Field(default=None, description="Primary measurement unit (e.g. ms, rps, bytes, queries)")
    source_type: str = Field(description="Source of telemetry: opentelemetry, sql_log, playwright, ast_parser, or http_metric")
    artifact_reference: Optional[str] = Field(default=None, description="Path to raw telemetry artifact or dump file")
    trace_id: Optional[str] = Field(default=None, description="OpenTelemetry or distributed trace identifier")
    span_id: Optional[str] = Field(default=None, description="OpenTelemetry span identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of collection")
    git_commit: Optional[str] = Field(default=None, description="Git commit hash at time of observation")
    environment_fingerprint: Optional[str] = Field(default=None, description="OS, runtime, and hardware fingerprint")
    collection_method: Optional[str] = Field(default=None, description="Collection method or tool invoked")
    tool_version: Optional[str] = Field(default=None, description="Version of the diagnostic tool or SDK")
    source_references: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="List of verified source references {file_path, start_line, end_line, symbol}"
    )
    provenance: Optional[str] = Field(default="deterministic_collector", description="Origin of this evidence record")
    limitations: Optional[str] = Field(default=None, description="Known limitations or caveats of this measurement")

    model_config = ConfigDict(from_attributes=True)

class EvidenceListResponse(BaseModel):
    run_id: str
    total_count: int
    items: List[EvidenceRecord]

    model_config = ConfigDict(from_attributes=True)
