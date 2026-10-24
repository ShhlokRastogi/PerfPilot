import React, { useState } from 'react';
import { Diagnosis, ApprovalStatus } from '../types';
import { 
  ShieldAlert, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Sparkles, 
  Layers, 
  Lock,
  FileCheck
} from 'lucide-react';
import { DiffViewer } from './DiffViewer';

interface ApprovalGateProps {
  runId: string;
  diagnosis: Diagnosis;
  onDecision: (decision: ApprovalStatus, reason?: string) => Promise<void>;
  loading: boolean;
}

export const ApprovalGate: React.FC<ApprovalGateProps> = ({
  runId,
  diagnosis,
  onDecision,
  loading,
}) => {
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);

  return (
    <div className="bg-gradient-to-b from-slate-900 to-slate-950 border-2 border-amber-500/40 rounded-2xl p-6 shadow-2xl shadow-amber-500/5 my-6">
      {/* Header Banner */}
      <div className="flex items-start justify-between border-b border-slate-800 pb-5 mb-5">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <ShieldAlert className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-slate-100 tracking-tight">
                Human Approval Gate Required
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-300 border border-amber-500/30">
                ACTION REQUIRED
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Review diagnostic evidence, risk assessment, and cryptographic patch hash before sandbox execution.
            </p>
          </div>
        </div>

        {/* Cryptographic Hash Lock */}
        <div className="text-right">
          <div className="flex items-center gap-1.5 text-xs font-mono text-cyan-400 justify-end">
            <Lock className="w-3.5 h-3.5" />
            <span>SHA-256 Patch Hash</span>
          </div>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5 bg-slate-950 px-2 py-1 rounded border border-slate-800 max-w-xs truncate" title={diagnosis.patch_hash}>
            {diagnosis.patch_hash}
          </div>
        </div>
      </div>

      {/* Diagnostic Overview Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Expected Benefit */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-1.5">
            <Sparkles className="w-4 h-4" />
            Expected Benefit (Model Estimate)
          </div>
          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            {diagnosis.expected_benefit}
          </p>
          <div className="mt-2 text-[11px] text-slate-500 font-mono">
            Confidence: <span className="text-cyan-400 font-semibold">{Math.round(diagnosis.confidence_score * 100)}%</span>
            {diagnosis.uncertainty_notes && ` — ${diagnosis.uncertainty_notes}`}
          </div>
        </div>

        {/* Potential Risks */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-rose-400 uppercase tracking-wider mb-1.5">
            <AlertTriangle className="w-4 h-4" />
            Potential Risks & Operational Checks
          </div>
          <ul className="text-xs text-slate-300 space-y-1">
            {diagnosis.risks.map((risk, idx) => (
              <li key={idx} className="flex items-start gap-1.5">
                <span className="text-rose-400 mt-0.5">•</span>
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Regression Verification Plan */}
      <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 mb-6">
        <div className="flex items-center gap-2 text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2">
          <FileCheck className="w-4 h-4" />
          Pre-deployment Regression Test Plan
        </div>
        <div className="flex flex-wrap gap-2">
          {diagnosis.regression_test_plan.map((test, idx) => (
            <span key={idx} className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 font-mono text-xs border border-slate-700">
              ✓ {test}
            </span>
          ))}
        </div>
      </div>

      {/* Proposed Unified Diff */}
      <div className="mb-6">
        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center justify-between">
          <span>Target Patch Diff</span>
          <span className="text-slate-500 font-normal">Files: {diagnosis.affected_files.join(', ')}</span>
        </div>
        <DiffViewer
          diff={diagnosis.proposed_patch_diff}
          affectedFiles={diagnosis.affected_files}
          patchHash={diagnosis.patch_hash}
        />
      </div>

      {/* Action Controls */}
      <div className="border-t border-slate-800 pt-5">
        {!showRejectForm ? (
          <div className="flex items-center justify-between">
            <div className="text-xs text-slate-400">
              Approving authorizes execution <span className="text-slate-200 font-medium">only inside a disposable sandbox</span> with regression validation.
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setShowRejectForm(true)}
                disabled={loading}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-rose-300 text-xs font-semibold transition-colors flex items-center gap-1.5 border border-slate-700 disabled:opacity-50"
              >
                <XCircle className="w-4 h-4 text-rose-400" />
                Reject Patch
              </button>
              <button
                type="button"
                onClick={() => onDecision('approved')}
                disabled={loading}
                className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-lg shadow-emerald-600/20 flex items-center gap-2 disabled:opacity-50"
              >
                <CheckCircle className="w-4 h-4" />
                {loading ? 'Authorizing...' : 'Approve & Execute Patch'}
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-slate-950 p-4 rounded-xl border border-rose-900/50">
            <h4 className="text-xs font-semibold text-rose-300 mb-2">Provide Reason for Rejection</h4>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Requires manual index creation before query join..."
              rows={2}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 placeholder-slate-500 font-sans focus:outline-none focus:border-rose-500 mb-3"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowRejectForm(false)}
                className="px-3 py-1.5 rounded text-xs text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => onDecision('rejected', rejectReason)}
                disabled={loading}
                className="px-4 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
              >
                Confirm Permanent Rejection
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
