export type RunStatus =
  | 'created'
  | 'validating'
  | 'preparing_baseline'
  | 'benchmarking_baseline'
  | 'diagnosing'
  | 'awaiting_approval'
  | 'rejected'
  | 'applying_patch'
  | 'testing_candidate'
  | 'benchmarking_candidate'
  | 'verifying'
  | 'completed'
  | 'failed';

export type Verdict =
  | 'verified_improvement'
  | 'no_improvement'
  | 'regression'
  | 'inconclusive'
  | 'failed';

export type ApprovalStatus = 'pending' | 'approved' | 'rejected';

export interface PersonaConfig {
  role: string;
  traffic_pct: number;
  path: string;
  headers?: Record<string, string>;
}

export interface SandboxStep {
  step_id: string;
  name: string;
  status: 'running' | 'completed' | 'failed' | 'skipped';
  output: string;
  duration_ms: number;
  timestamp: number;
}

export interface Run {
  id: string;
  status: RunStatus;
  target_type: string;
  target_url: string;
  repo_path: string;
  objectives: {
    p95_latency_ms?: number;
    min_speedup_factor?: number;
    max_error_rate_pct?: number;
    [key: string]: any;
  };
  workload_config: {
    vus?: number;
    duration_sec?: number;
    concurrency?: number;
    personas?: PersonaConfig[];
    [key: string]: any;
  };
  failure_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BenchmarkMetric {
  id: number;
  run_id: string;
  phase: 'baseline' | 'candidate';
  p50_latency_ms: number;
  p90_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  avg_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
  throughput_rps: number;
  total_requests: number;
  failed_requests: number;
  error_rate_pct: number;
  duration_sec: number;
  lcp_ms?: number | null;
  ttfb_ms?: number | null;
  raw_data?: Record<string, any>;
  created_at: string;
}

export interface HypothesisItem {
  id: string;
  title: string;
  description: string;
  likelihood: string;
  evidence: string;
}

export interface CodeLocation {
  file_path: string;
  start_line: number;
  end_line: number;
  snippet: string;
  explanation: string;
}

export interface Diagnosis {
  id: number;
  run_id: string;
  summary: string;
  symptoms: string[];
  ranked_hypotheses: HypothesisItem[];
  supporting_measurements: Record<string, any>;
  supporting_code_locations: CodeLocation[];
  confidence_score: number;
  uncertainty_notes: string;
  proposed_patch_diff: string;
  patch_hash: string;
  affected_files: string[];
  expected_benefit: string;
  risks: string[];
  regression_test_plan: string[];
  created_at: string;
}

export interface PatchApproval {
  id: number;
  run_id: string;
  status: ApprovalStatus;
  patch_hash: string;
  reviewed_by?: string | null;
  decision_reason?: string | null;
  decided_at?: string | null;
}

export interface RunReport {
  id: number;
  run_id: string;
  verdict: Verdict;
  summary: string;
  p95_baseline_ms: number;
  p95_candidate_ms: number;
  p95_improvement_pct: number;
  throughput_baseline_rps: number;
  throughput_candidate_rps: number;
  throughput_improvement_pct: number;
  regression_passed: boolean;
  objectives_met: boolean;
  is_conclusive: boolean;
  details: Record<string, any>;
  created_at: string;
}

export interface AuditEvent {
  id: number;
  run_id: string;
  event_type: string;
  from_state?: string | null;
  to_state?: string | null;
  message: string;
  details: Record<string, any>;
  timestamp: string;
}

export interface EvidenceRecord {
  evidence_id: string;
  run_id: string;
  finding_id?: string | null;
  category: 'backend' | 'database' | 'frontend' | 'repository' | 'critic' | 'router';
  observation: string;
  measured_values: Record<string, any>;
  unit?: string | null;
  source_type: string;
  artifact_reference?: string | null;
  trace_id?: string | null;
  span_id?: string | null;
  timestamp: string;
  git_commit?: string | null;
  environment_fingerprint?: string | null;
  collection_method?: string | null;
  tool_version?: string | null;
  source_references?: Array<{
    file_path: string;
    start_line: number;
    end_line: number;
    snippet?: string;
    explanation?: string;
  }>;
  provenance?: string | null;
  limitations?: string | null;
}
