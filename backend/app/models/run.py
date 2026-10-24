import enum
from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Enum, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class RunStatus(str, enum.Enum):
    CREATED = "created"
    VALIDATING = "validating"
    PREPARING_BASELINE = "preparing_baseline"
    BENCHMARKING_BASELINE = "benchmarking_baseline"
    DIAGNOSING = "diagnosing"
    AWAITING_APPROVAL = "awaiting_approval"
    REJECTED = "rejected"
    APPLYING_PATCH = "applying_patch"
    TESTING_CANDIDATE = "testing_candidate"
    BENCHMARKING_CANDIDATE = "benchmarking_candidate"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"

class Verdict(str, enum.Enum):
    VERIFIED_IMPROVEMENT = "verified_improvement"
    NO_IMPROVEMENT = "no_improvement"
    REGRESSION = "regression"
    INCONCLUSIVE = "inconclusive"
    FAILED = "failed"

class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Run(Base):
    __tablename__ = "runs"

    id = Column(String(36), primary_key=True, index=True)
    status = Column(String(32), default=RunStatus.CREATED.value, index=True, nullable=False)
    target_type = Column(String(32), default="demo", nullable=False)
    target_url = Column(String(512), nullable=False)
    repo_path = Column(String(512), default="demo-app", nullable=False)
    
    # User objectives (e.g., {"p95_latency_ms": 200, "min_speedup_factor": 2.0, "max_error_rate_pct": 1.0})
    objectives = Column(JSON, default=dict)
    
    # Workload parameters (e.g., {"vus": 10, "duration_sec": 10, "endpoint": "/api/products"})
    workload_config = Column(JSON, default=dict)
    
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    audit_events = relationship("AuditEvent", back_populates="run", cascade="all, delete-orphan", order_by="AuditEvent.timestamp")
    metrics = relationship("BenchmarkMetric", back_populates="run", cascade="all, delete-orphan")
    evidence = relationship("EvidenceModel", back_populates="run", cascade="all, delete-orphan", order_by="EvidenceModel.timestamp")
    diagnosis = relationship("DiagnosisModel", back_populates="run", uselist=False, cascade="all, delete-orphan")
    patch_approval = relationship("PatchApproval", back_populates="run", uselist=False, cascade="all, delete-orphan")
    report = relationship("RunReport", back_populates="run", uselist=False, cascade="all, delete-orphan")

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    from_state = Column(String(32), nullable=True)
    to_state = Column(String(32), nullable=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("Run", back_populates="audit_events")

class BenchmarkMetric(Base):
    __tablename__ = "benchmark_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, index=True)
    phase = Column(String(16), nullable=False) # "baseline" or "candidate"
    
    p50_latency_ms = Column(Float, nullable=False)
    p90_latency_ms = Column(Float, nullable=False)
    p95_latency_ms = Column(Float, nullable=False)
    p99_latency_ms = Column(Float, nullable=False)
    avg_latency_ms = Column(Float, nullable=False)
    min_latency_ms = Column(Float, default=0.0)
    max_latency_ms = Column(Float, default=0.0)
    
    throughput_rps = Column(Float, nullable=False)
    total_requests = Column(Integer, nullable=False)
    failed_requests = Column(Integer, default=0)
    error_rate_pct = Column(Float, default=0.0)
    duration_sec = Column(Float, nullable=False)
    
    # Browser metrics if collected
    lcp_ms = Column(Float, nullable=True)
    ttfb_ms = Column(Float, nullable=True)
    
    raw_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("Run", back_populates="metrics")

class DiagnosisModel(Base):
    __tablename__ = "diagnoses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, unique=True, index=True)
    
    summary = Column(Text, nullable=False)
    symptoms = Column(JSON, default=list) # List[str]
    ranked_hypotheses = Column(JSON, default=list) # List[Dict]
    supporting_measurements = Column(JSON, default=dict)
    supporting_code_locations = Column(JSON, default=list)
    confidence_score = Column(Float, default=0.9)
    uncertainty_notes = Column(Text, default="")
    
    proposed_patch_diff = Column(Text, nullable=False)
    patch_hash = Column(String(64), nullable=False, index=True) # SHA-256
    affected_files = Column(JSON, default=list)
    expected_benefit = Column(Text, default="")
    risks = Column(JSON, default=list)
    regression_test_plan = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("Run", back_populates="diagnosis")

class PatchApproval(Base):
    __tablename__ = "patch_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, unique=True, index=True)
    
    status = Column(String(16), default=ApprovalStatus.PENDING.value, nullable=False)
    patch_hash = Column(String(64), nullable=False)
    reviewed_by = Column(String(64), nullable=True)
    decision_reason = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)

    run = relationship("Run", back_populates="patch_approval")

class RunReport(Base):
    __tablename__ = "run_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, unique=True, index=True)
    
    verdict = Column(String(32), nullable=False) # Verdict enum value
    summary = Column(Text, nullable=False)
    
    p95_baseline_ms = Column(Float, nullable=False)
    p95_candidate_ms = Column(Float, nullable=False)
    p95_improvement_pct = Column(Float, nullable=False)
    
    throughput_baseline_rps = Column(Float, nullable=False)
    throughput_candidate_rps = Column(Float, nullable=False)
    throughput_improvement_pct = Column(Float, nullable=False)
    
    regression_passed = Column(Boolean, default=True)
    objectives_met = Column(Boolean, default=True)
    is_conclusive = Column(Boolean, default=True)
    
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    run = relationship("Run", back_populates="report")

class EvidenceModel(Base):
    __tablename__ = "evidence_records"

    evidence_id = Column(String(36), primary_key=True, index=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, index=True)
    finding_id = Column(String(64), nullable=True)
    category = Column(String(32), nullable=False) # backend, database, frontend, repository, critic
    observation = Column(Text, nullable=False)
    measured_values = Column(JSON, default=dict)
    unit = Column(String(32), nullable=True)
    source_type = Column(String(32), nullable=False) # opentelemetry, sql_log, playwright, ast_parser, http_metric
    artifact_reference = Column(String(512), nullable=True)
    trace_id = Column(String(64), nullable=True)
    span_id = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    git_commit = Column(String(64), nullable=True)
    environment_fingerprint = Column(String(128), nullable=True)
    collection_method = Column(String(64), nullable=True)
    tool_version = Column(String(32), nullable=True)
    source_references = Column(JSON, default=list)
    provenance = Column(String(64), default="deterministic_collector")
    limitations = Column(Text, nullable=True)

    run = relationship("Run", back_populates="evidence")
