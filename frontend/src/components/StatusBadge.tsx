import React from 'react';
import { RunStatus, Verdict } from '../types';
import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Clock, 
  Cpu, 
  Activity, 
  ShieldCheck, 
  Flame,
  Check
} from 'lucide-react';

interface StatusBadgeProps {
  status: RunStatus | string;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs font-medium',
    lg: 'px-3 py-1.5 text-sm font-semibold',
  }[size];

  switch (status) {
    case 'awaiting_approval':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 ${sizeClasses} animate-pulse`}>
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          Awaiting Human Approval
        </span>
      );
    case 'completed':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 ${sizeClasses}`}>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          Completed
        </span>
      );
    case 'failed':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 ${sizeClasses}`}>
          <XCircle className="w-3.5 h-3.5 text-rose-400" />
          Failed
        </span>
      );
    case 'rejected':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full bg-slate-500/10 text-slate-400 border border-slate-500/30 ${sizeClasses}`}>
          <XCircle className="w-3.5 h-3.5 text-slate-400" />
          Rejected by Reviewer
        </span>
      );
    case 'diagnosing':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 ${sizeClasses} animate-pulse`}>
          <Cpu className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
          AI Diagnosis Active
        </span>
      );
    case 'benchmarking_baseline':
    case 'benchmarking_candidate':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 ${sizeClasses} animate-pulse`}>
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          Benchmarking Workload
        </span>
      );
    case 'testing_candidate':
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/30 ${sizeClasses} animate-pulse`}>
          <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
          Regression Testing
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/30 ${sizeClasses}`}>
          <Clock className="w-3.5 h-3.5 text-sky-400" />
          {status.replace(/_/g, ' ')}
        </span>
      );
  }
};

export const VerdictBadge: React.FC<{ verdict: Verdict | string }> = ({ verdict }) => {
  switch (verdict) {
    case 'verified_improvement':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 text-xs font-semibold uppercase tracking-wider">
          <Check className="w-4 h-4 text-emerald-400" />
          Verified Improvement
        </span>
      );
    case 'regression':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/40 text-xs font-semibold uppercase tracking-wider">
          <Flame className="w-4 h-4 text-rose-400" />
          Regression Detected
        </span>
      );
    case 'no_improvement':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/40 text-xs font-semibold uppercase tracking-wider">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          No Improvement
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-500/15 text-slate-400 border border-slate-500/40 text-xs font-semibold uppercase tracking-wider">
          <Clock className="w-4 h-4 text-slate-400" />
          {verdict.replace(/_/g, ' ')}
        </span>
      );
  }
};
