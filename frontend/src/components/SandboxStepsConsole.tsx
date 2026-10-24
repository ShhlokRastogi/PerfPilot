import React, { useState } from 'react';
import { SandboxStep } from '../types';
import { 
  Box, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  Clock, 
  Terminal, 
  ChevronDown, 
  ChevronRight,
  ShieldCheck,
  FileCode,
  Zap,
  Trash2
} from 'lucide-react';

interface SandboxStepsConsoleProps {
  steps: SandboxStep[];
  activeRunStatus: string;
}

const STEP_ICONS: Record<string, React.ReactNode> = {
  baseline_prep: <Box className="w-4 h-4 text-cyan-400" />,
  baseline_detect: <ShieldCheck className="w-4 h-4 text-emerald-400" />,
  baseline_launch: <Terminal className="w-4 h-4 text-blue-400" />,
  provision: <Box className="w-4 h-4 text-cyan-400" />,
  patch: <FileCode className="w-4 h-4 text-amber-400" />,
  syntax: <ShieldCheck className="w-4 h-4 text-emerald-400" />,
  test: <Zap className="w-4 h-4 text-purple-400" />,
  regression: <Zap className="w-4 h-4 text-purple-400" />,
  candidate_detect: <ShieldCheck className="w-4 h-4 text-emerald-400" />,
  candidate_launch: <Terminal className="w-4 h-4 text-blue-400" />,
  launch: <Terminal className="w-4 h-4 text-blue-400" />,
  bench: <Zap className="w-4 h-4 text-amber-400" />,
  teardown: <Trash2 className="w-4 h-4 text-rose-400" />,
};

export const SandboxStepsConsole: React.FC<SandboxStepsConsoleProps> = ({ steps, activeRunStatus }) => {
  const [expandedStepId, setExpandedStepId] = useState<string | null>(null);
  const [expandAll, setExpandAll] = useState<boolean>(true);

  const toggleExpand = (stepId: string) => {
    if (expandAll) {
      setExpandAll(false);
      setExpandedStepId(null);
    } else {
      setExpandedStepId(expandedStepId === stepId ? null : stepId);
    }
  };

  const isExecuting = ['validating', 'preparing_baseline', 'benchmarking_baseline', 'applying_patch', 'testing_candidate', 'benchmarking_candidate'].includes(activeRunStatus);

  if (!steps || steps.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Box className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-slate-200">Sandbox Isolation & Step Execution</h2>
          </div>
          <span className="text-[11px] font-mono text-slate-500">Standby</span>
        </div>
        <p className="text-xs text-slate-400">
          Sandbox execution steps and server process logs will appear here in real time as the application is auto-booted and tested.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <Box className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-semibold text-slate-200">
            Sandbox Isolation Execution Pipeline
          </h2>
          {isExecuting && (
            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Loader2 className="w-3 h-3 animate-spin" /> Live Sandboxing
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setExpandAll(!expandAll)}
            className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300 bg-cyan-950/40 border border-cyan-800/40 px-2 py-0.5 rounded transition-colors"
          >
            {expandAll ? 'Collapse Logs' : 'Expand All Logs'}
          </button>
          <span className="text-xs font-mono text-slate-400">
            {steps.filter(s => s.status === 'completed').length} / {steps.length} Steps Completed
          </span>
        </div>
      </div>

      <div className="space-y-2 font-sans">
        {steps.map((step) => {
          const isExpanded = expandAll || expandedStepId === step.step_id;
          const icon = STEP_ICONS[step.step_id] || <Box className="w-4 h-4 text-slate-400" />;

          return (
            <div 
              key={step.step_id}
              className={`rounded-xl border transition-all ${
                step.status === 'running'
                  ? 'bg-slate-950/90 border-cyan-500/50 shadow-lg shadow-cyan-950/20'
                  : step.status === 'failed'
                  ? 'bg-slate-950/90 border-rose-500/50'
                  : 'bg-slate-950/50 border-slate-800/80 hover:border-slate-700'
              }`}
            >
              <div 
                className="p-3 flex items-center justify-between cursor-pointer select-none"
                onClick={() => toggleExpand(step.step_id)}
              >
                <div className="flex items-center gap-3">
                  <div className="p-1.5 rounded-lg bg-slate-900 border border-slate-800">
                    {icon}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-200">{step.name}</span>
                      <span className="text-[10px] font-mono text-slate-500">({step.step_id})</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {step.duration_ms > 0 && (
                    <span className="flex items-center gap-1 text-[11px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {step.duration_ms < 1000 
                        ? `${step.duration_ms.toFixed(0)}ms` 
                        : `${(step.duration_ms / 1000).toFixed(2)}s`}
                    </span>
                  )}

                  {step.status === 'completed' && (
                    <span className="flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      <CheckCircle2 className="w-3 h-3" /> Done
                    </span>
                  )}

                  {step.status === 'running' && (
                    <span className="flex items-center gap-1 text-[11px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/30">
                      <Loader2 className="w-3 h-3 animate-spin" /> In Progress
                    </span>
                  )}

                  {step.status === 'failed' && (
                    <span className="flex items-center gap-1 text-[11px] font-mono text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                      <XCircle className="w-3 h-3" /> Failed
                    </span>
                  )}

                  {step.status === 'skipped' && (
                    <span className="text-[11px] font-mono text-slate-500 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      Skipped
                    </span>
                  )}

                  <button className="text-slate-500 hover:text-slate-300">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Collapsible Console Output Drawer */}
              {isExpanded && (
                <div className="border-t border-slate-800/80 bg-black/50 p-3 rounded-b-xl">
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1.5">
                    <span className="flex items-center gap-1.5 text-slate-300">
                      <Terminal className="w-3 h-3 text-cyan-400" /> Execution Console Log
                    </span>
                    <span className="text-slate-500">
                      Recorded at {new Date(step.timestamp * 1000).toLocaleTimeString()}
                    </span>
                  </div>
                  <pre className="text-[11px] font-mono text-slate-300 bg-slate-950 p-3 rounded-lg border border-slate-900 overflow-x-auto whitespace-pre-wrap max-h-56 leading-relaxed">
                    {step.output || '// No terminal output logged for this step.'}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
