import React, { useEffect, useState } from 'react';
import { Run } from '../types';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { 
  Activity, 
  CheckCircle2, 
  XCircle, 
  TrendingUp, 
  ArrowRight, 
  RefreshCw,
  PlusCircle,
  Zap,
  Trash2
} from 'lucide-react';

interface OverviewPageProps {
  onSelectRun: (runId: string) => void;
  onNewAnalysis: () => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ onSelectRun, onNewAnalysis }) => {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  const loadRuns = async () => {
    try {
      setLoading(true);
      const data = await api.listRuns();
      setRuns(data);
    } catch (err) {
      console.error('Failed to load runs:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleClearRuns = async () => {
    if (window.confirm('Are you sure you want to clear all recent runs and artifacts?')) {
      try {
        setLoading(true);
        await api.clearAllRuns();
        await loadRuns();
      } catch (err) {
        console.error('Failed to clear runs:', err);
      } finally {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const totalRuns = runs.length;
  const completedRuns = runs.filter((r) => r.status === 'completed').length;
  const awaitingApprovalRuns = runs.filter((r) => r.status === 'awaiting_approval').length;
  const failedRuns = runs.filter((r) => r.status === 'failed' || r.status === 'rejected').length;

  return (
    <div className="space-y-8">
      {/* Top Hero / Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2.5">
            Performance Engineering Control Plane
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Automated benchmark ingestion, LLM root-cause diagnosis, cryptographic approval gates, and candidate verification.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {runs.length > 0 && (
            <button
              onClick={handleClearRuns}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-rose-400 hover:text-rose-300 hover:border-rose-900/50 text-xs font-medium transition-colors"
              title="Clear all run history"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear History
            </button>
          )}
          <button
            onClick={loadRuns}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
            title="Refresh Runs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={onNewAnalysis}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-600/20 transition-all"
          >
            <PlusCircle className="w-4 h-4" />
            Start Analysis Run
          </button>
        </div>
      </div>

      {/* Metric Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">
            <span>Total Analysis Runs</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-3xl font-bold font-mono text-slate-100">{totalRuns}</div>
          <p className="text-[11px] text-slate-500 mt-1">Autonomous evaluation sessions</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">
            <span>Verified Improvements</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold font-mono text-emerald-400">{completedRuns}</div>
          <p className="text-[11px] text-slate-500 mt-1">SLA objectives met & verified</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">
            <span>Awaiting Human Gate</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-bold font-mono text-amber-400">{awaitingApprovalRuns}</div>
          <p className="text-[11px] text-slate-500 mt-1">Exact patch hash review pending</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">
            <span>Halted / Rejections</span>
            <XCircle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-3xl font-bold font-mono text-rose-400">{failedRuns}</div>
          <p className="text-[11px] text-slate-500 mt-1">Rollbacks or reviewer rejections</p>
        </div>
      </div>

      {/* Recent Runs Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200">Recent Engineering Runs</h2>
          <span className="text-xs text-slate-500 font-mono">{runs.length} runs recorded</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500 font-mono">
            Loading runs...
          </div>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center">
            <Zap className="w-8 h-8 text-slate-600 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-300">No runs launched yet</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Launch your first autonomous performance analysis against any local application or staging service.
            </p>
            <button
              onClick={onNewAnalysis}
              className="mt-4 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-600/20"
            >
              Start Performance Analysis
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4 font-medium">Run ID</th>
                  <th className="py-3 px-4 font-medium">Status</th>
                  <th className="py-3 px-4 font-medium">Target Endpoint</th>
                  <th className="py-3 px-4 font-medium">Workload</th>
                  <th className="py-3 px-4 font-medium">Target SLA</th>
                  <th className="py-3 px-4 font-medium">Created</th>
                  <th className="py-3 px-4 text-right font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {runs.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 text-cyan-400 font-bold">
                      {r.id.substring(0, 8)}...
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={r.status} size="sm" />
                    </td>
                    <td className="py-3 px-4 text-slate-300 truncate max-w-xs" title={r.target_url}>
                      {r.target_url}
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {r.workload_config?.vus || 10} VUs ({r.workload_config?.duration_sec || 10}s)
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      p95 &lt; {r.objectives?.p95_latency_ms || 250}ms
                    </td>
                    <td className="py-3 px-4 text-slate-500 text-[11px]" title={new Date(r.created_at).toLocaleString()}>
                      {new Date(r.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}{' '}
                      {new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => onSelectRun(r.id)}
                        className="px-3 py-1 rounded bg-slate-800 hover:bg-cyan-600 hover:text-white text-slate-300 font-sans text-xs transition-colors inline-flex items-center gap-1"
                      >
                        <span>Inspect</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
