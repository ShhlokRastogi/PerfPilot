import React, { useEffect, useState } from 'react';
import { 
  Run, 
  BenchmarkMetric, 
  Diagnosis, 
  PatchApproval, 
  RunReport, 
  AuditEvent, 
  ApprovalStatus,
  SandboxStep,
  EvidenceRecord
} from '../types';
import { api } from '../api/client';
import { StatusBadge, VerdictBadge } from '../components/StatusBadge';
import { MetricCard } from '../components/MetricCard';
import { LatencyChart } from '../components/LatencyChart';
import { ApprovalGate } from '../components/ApprovalGate';
import { DiffViewer } from '../components/DiffViewer';
import { SandboxStepsConsole } from '../components/SandboxStepsConsole';
import { 
  ArrowLeft, 
  Download, 
  RefreshCw, 
  Activity, 
  Cpu, 
  ShieldCheck, 
  Clock, 
  Terminal, 
  Layers, 
  FileText,
  AlertCircle
} from 'lucide-react';

interface RunDetailsPageProps {
  runId: string;
  onBack: () => void;
}

const WORKFLOW_STEPS = [
  { key: 'created', label: 'Created' },
  { key: 'validating', label: 'Validate' },
  { key: 'benchmarking_baseline', label: 'Baseline Benchmark' },
  { key: 'diagnosing', label: 'AI Diagnosis' },
  { key: 'awaiting_approval', label: 'Human Gate' },
  { key: 'applying_patch', label: 'Sandbox Patch' },
  { key: 'testing_candidate', label: 'Regression Tests' },
  { key: 'benchmarking_candidate', label: 'Candidate Benchmark' },
  { key: 'verifying', label: 'Verification' },
  { key: 'completed', label: 'Final Report' },
];

export const RunDetailsPage: React.FC<RunDetailsPageProps> = ({ runId, onBack }) => {
  const [run, setRun] = useState<Run | null>(null);
  const [metrics, setMetrics] = useState<BenchmarkMetric[]>([]);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [report, setReport] = useState<RunReport | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [sandboxSteps, setSandboxSteps] = useState<SandboxStep[]>([]);
  const [evidenceRecords, setEvidenceRecords] = useState<EvidenceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [approvalActionLoading, setApprovalActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRunData = async () => {
    try {
      const runData = await api.getRun(runId);
      setRun(runData);

      // Fetch metrics
      const metricsData = await api.getRunMetrics(runId);
      setMetrics(metricsData);

      // Fetch diagnosis if available
      try {
        const diagData = await api.getRunDiagnosis(runId);
        setDiagnosis(diagData);
      } catch {
        // Diagnosis might not be generated yet
      }

      // Fetch report if completed
      try {
        const repData = await api.getRunReport(runId);
        setReport(repData);
      } catch {
        // Report not ready yet
      }

      // Fetch audit events
      try {
        const auditData = await api.getRunAudit(runId);
        setAuditEvents(auditData);
      } catch {
        // ignore
      }

      // Fetch sandbox execution steps
      try {
        const stepsData = await api.getSandboxSteps(runId);
        setSandboxSteps(stepsData);
      } catch {
        // ignore
      }

      // Fetch empirical evidence records
      try {
        const evData = await api.getRunEvidence(runId);
        setEvidenceRecords(evData);
      } catch {
        // ignore
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch run data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRunData();

    // Poll every 2 seconds while run is active
    const interval = setInterval(() => {
      if (run && ['completed', 'failed', 'rejected'].includes(run.status)) {
        return;
      }
      fetchRunData();
    }, 2000);

    return () => clearInterval(interval);
  }, [runId, run?.status]);

  const handleApprovalDecision = async (decision: ApprovalStatus, reason?: string) => {
    if (!diagnosis) return;
    setApprovalActionLoading(true);
    try {
      await api.submitApproval(runId, {
        patch_hash: diagnosis.patch_hash,
        decision,
        reviewed_by: 'lead_performance_engineer',
        decision_reason: reason,
      });
      await fetchRunData();
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    } finally {
      setApprovalActionLoading(false);
    }
  };

  const baselineMetric = metrics.find((m) => m.phase === 'baseline');
  const candidateMetric = metrics.find((m) => m.phase === 'candidate');

  const handleDownloadReport = () => {
    const reportData = {
      run,
      metrics,
      diagnosis,
      report,
      auditEvents,
    };
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `perfpilot_report_${runId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading && !run) {
    return (
      <div className="h-96 flex flex-col items-center justify-center text-slate-500 font-mono text-xs gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
        <span>Loading performance run details...</span>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
        <h2 className="text-base font-semibold text-slate-200">Run Not Found</h2>
        <button onClick={onBack} className="mt-4 px-3 py-1.5 rounded bg-slate-800 text-xs">
          Return to Overview
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold font-mono text-slate-100">
                Run #{run.id.substring(0, 8)}
              </h1>
              <StatusBadge status={run.status} size="md" />
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Target: <span className="text-slate-300">{run.target_url}</span> ({run.repo_path})
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchRunData}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200"
            title="Refresh Status"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleDownloadReport}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            Export Audit Report
          </button>
        </div>
      </div>

      {/* Stepper Progress Bar */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 overflow-x-auto">
        <div className="flex items-center justify-between min-w-[700px]">
          {WORKFLOW_STEPS.map((step, idx) => {
            const isCurrent = run.status === step.key;
            const isDone = [
              'completed',
              ...(run.status === 'awaiting_approval' ? ['created', 'validating', 'benchmarking_baseline', 'diagnosing'] : []),
              ...(run.status === 'benchmarking_candidate' ? ['created', 'validating', 'benchmarking_baseline', 'diagnosing', 'awaiting_approval', 'applying_patch', 'testing_candidate'] : []),
              ...(run.status === 'verifying' ? ['created', 'validating', 'benchmarking_baseline', 'diagnosing', 'awaiting_approval', 'applying_patch', 'testing_candidate', 'benchmarking_candidate'] : []),
            ].includes(step.key);

            return (
              <div key={step.key} className="flex items-center gap-2">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold font-mono transition-colors ${
                    isCurrent
                      ? 'bg-cyan-500 text-slate-950 ring-4 ring-cyan-500/20 animate-pulse'
                      : isDone
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                      : 'bg-slate-800 text-slate-500'
                  }`}
                >
                  {idx + 1}
                </div>
                <span
                  className={`text-xs whitespace-nowrap ${
                    isCurrent
                      ? 'font-bold text-cyan-300'
                      : isDone
                      ? 'text-slate-300'
                      : 'text-slate-500'
                  }`}
                >
                  {step.label}
                </span>
                {idx < WORKFLOW_STEPS.length - 1 && (
                  <div className="w-4 h-0.5 bg-slate-800 mx-1" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Final Verdict Banner (If Completed or Failed) */}
      {report && (
        <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 border-2 border-emerald-500/40 rounded-2xl p-6 shadow-xl">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3">
                <VerdictBadge verdict={report.verdict} />
                <span className="text-xs text-slate-400 font-mono">
                  Deterministic Verification Complete
                </span>
              </div>
              <p className="text-sm font-medium text-slate-200 mt-2 leading-relaxed">
                {report.summary}
              </p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-extrabold text-emerald-400 font-mono">
                +{report.p95_improvement_pct}%
              </div>
              <div className="text-xs text-slate-400 font-mono">p95 Latency Reduction</div>
            </div>
          </div>
        </div>
      )}

      {/* HUMAN APPROVAL GATE COMPONENT (When in awaiting_approval) */}
      {run.status === 'awaiting_approval' && diagnosis && (
        <ApprovalGate
          runId={run.id}
          diagnosis={diagnosis}
          onDecision={handleApprovalDecision}
          loading={approvalActionLoading}
        />
      )}

      {/* Core Metrics Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          label="p95 Latency"
          baseline={baselineMetric?.p95_latency_ms ?? '--'}
          candidate={candidateMetric?.p95_latency_ms}
          unit="ms"
          improvementPct={report?.p95_improvement_pct}
          lowerIsBetter={true}
        />
        <MetricCard
          label="p50 (Median) Latency"
          baseline={baselineMetric?.p50_latency_ms ?? '--'}
          candidate={candidateMetric?.p50_latency_ms}
          unit="ms"
          lowerIsBetter={true}
        />
        <MetricCard
          label="Throughput"
          baseline={baselineMetric?.throughput_rps ?? '--'}
          candidate={candidateMetric?.throughput_rps}
          unit=" req/s"
          improvementPct={report?.throughput_improvement_pct}
          lowerIsBetter={false}
        />
        <MetricCard
          label="HTTP Error Rate"
          baseline={`${baselineMetric?.error_rate_pct ?? 0}%`}
          candidate={candidateMetric ? `${candidateMetric.error_rate_pct}%` : undefined}
          lowerIsBetter={true}
        />
      </div>

      {/* Latency Quantiles Chart */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              Latency Percentiles Comparison (p50, p90, p95, p99)
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Measured under identical concurrency ({run.workload_config?.vus || 10} VUs, {run.workload_config?.duration_sec || 10}s)
            </p>
          </div>
        </div>
        <LatencyChart baselineMetric={baselineMetric} candidateMetric={candidateMetric} />
      </div>

      {/* AI Diagnosis & Evidence Section */}
      {diagnosis && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-indigo-400" />
              <h2 className="text-base font-bold text-slate-100">
                AI Bottleneck Diagnosis & Root Cause
              </h2>
            </div>
            <div className="text-xs font-mono text-slate-400">
              Confidence Score: <span className="text-cyan-400 font-semibold">{Math.round(diagnosis.confidence_score * 100)}%</span>
            </div>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
            {diagnosis.summary}
          </p>

          {/* Hypotheses List */}
          <div>
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Ranked Root-Cause Hypotheses
            </h3>
            <div className="space-y-2">
              {diagnosis.ranked_hypotheses.map((hyp) => (
                <div key={hyp.id} className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex items-start gap-3">
                  <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 font-mono text-xs font-bold">
                    {hyp.id}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-200">{hyp.title}</span>
                      <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                        {hyp.likelihood} Likelihood
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">{hyp.description}</p>
                    <p className="text-[11px] text-cyan-400/90 font-mono mt-1">
                      Evidence: {hyp.evidence}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Code Locations */}
          {diagnosis.supporting_code_locations.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Identified Code Locations
              </h3>
              <div className="space-y-2">
                {diagnosis.supporting_code_locations.map((loc, idx) => (
                  <div key={idx} className="bg-slate-950 rounded-xl border border-slate-800 overflow-hidden font-mono text-xs">
                    <div className="bg-slate-900 px-3 py-1.5 text-slate-400 flex items-center justify-between">
                      <span>{loc.file_path}:{loc.start_line}-{loc.end_line}</span>
                      <span className="text-[11px] text-slate-500">{loc.explanation}</span>
                    </div>
                    <pre className="p-3 text-slate-300 overflow-x-auto text-[11px]">
                      {loc.snippet}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Diff Viewer (When not in approval state) */}
          {run.status !== 'awaiting_approval' && (
            <div>
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Applied Optimization Patch
              </h3>
              <DiffViewer
                diff={diagnosis.proposed_patch_diff}
                affectedFiles={diagnosis.affected_files}
                patchHash={diagnosis.patch_hash}
              />
            </div>
          )}
        </div>
      )}

      {/* Live Sandbox Execution Console */}
      <SandboxStepsConsole steps={sandboxSteps} activeRunStatus={run.status} />

      {/* Empirical Evidence Collection Explorer */}
      {evidenceRecords.length > 0 && (
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Empirical Evidence Collection ({evidenceRecords.length} Records)
            </h2>
            <span className="text-[11px] font-mono text-slate-500">
              Deterministic Multi-Agent Telemetry
            </span>
          </div>

          <div className="space-y-2.5">
            {evidenceRecords.map((ev) => (
              <div
                key={ev.evidence_id}
                className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/90 text-xs space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                      ev.category === 'backend' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' :
                      ev.category === 'database' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                      ev.category === 'frontend' ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' :
                      ev.category === 'repository' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                      'bg-slate-800 text-slate-300'
                    }`}>
                      {ev.category}
                    </span>
                    <span className="text-slate-400 font-mono text-[11px]">
                      Source: {ev.source_type}
                    </span>
                    {ev.trace_id && (
                      <span className="text-slate-500 font-mono text-[10px]">
                        Trace: {ev.trace_id.slice(0, 12)}...
                      </span>
                    )}
                  </div>
                  <span className="text-slate-500 font-mono text-[10px]">
                    {new Date(ev.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <p className="text-slate-200 leading-relaxed font-sans">{ev.observation}</p>

                {ev.limitations && (
                  <div className="text-[11px] text-amber-400/80 bg-amber-950/20 border border-amber-900/30 px-2 py-1 rounded">
                    <span className="font-semibold">Limitation:</span> {ev.limitations}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Audit Trail & State Transitions */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-slate-400" />
            Audit Trail & State Machine Transitions
          </h2>
          <span className="text-[11px] font-mono text-slate-500">
            {auditEvents.length} events logged
          </span>
        </div>
        <div className="space-y-2 font-mono text-xs">
          {(() => {
            const baseEpoch = run.created_at
              ? new Date(run.created_at).getTime()
              : (auditEvents.length > 0 ? new Date(auditEvents[0].timestamp).getTime() : 0);

            return auditEvents.map((evt) => {
              const eventEpoch = new Date(evt.timestamp).getTime();
              const offsetSec = baseEpoch > 0 ? Math.max(0, (eventEpoch - baseEpoch) / 1000).toFixed(2) : '0.00';

              return (
                <div key={evt.id} className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 flex items-start justify-between">
                  <div>
                    <span className="text-cyan-400 font-bold mr-2">[{evt.event_type}]</span>
                    <span className="text-slate-300">{evt.message}</span>
                    {evt.from_state && evt.to_state && (
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        {evt.from_state} → {evt.to_state}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-4 font-mono text-[11px]">
                    <span className="text-cyan-400 bg-cyan-950/60 border border-cyan-800/40 px-1.5 py-0.5 rounded text-[10px]">
                      +{offsetSec}s
                    </span>
                    <span className="text-slate-500">
                      {new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                </div>
              );
            });
          })()}
        </div>
      </div>
    </div>
  );
};
