import React from 'react';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';

interface MetricCardProps {
  label: string;
  baseline: number | string;
  candidate?: number | string | null;
  unit?: string;
  improvementPct?: number | null;
  lowerIsBetter?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  baseline,
  candidate,
  unit = '',
  improvementPct,
  lowerIsBetter = true,
}) => {
  const isCandidatePresent = candidate !== undefined && candidate !== null;
  const isPositive = improvementPct !== undefined && improvementPct !== null && improvementPct > 0;
  const isNeutral = improvementPct === 0 || improvementPct === undefined || improvementPct === null;

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-sm hover:border-slate-700 transition-colors">
      <div className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">{label}</div>
      <div className="flex items-baseline justify-between">
        <div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {isCandidatePresent ? candidate : baseline}
            <span className="text-xs text-slate-400 font-normal ml-1">{unit}</span>
          </div>
          {isCandidatePresent && (
            <div className="text-xs text-slate-500 font-mono mt-0.5">
              Baseline: {baseline}{unit}
            </div>
          )}
        </div>

        {isCandidatePresent && improvementPct !== undefined && improvementPct !== null && (
          <div
            className={`flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-semibold font-mono ${
              isPositive
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : isNeutral
                ? 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
            }`}
          >
            {isPositive ? (
              <ArrowDownRight className="w-3.5 h-3.5" />
            ) : isNeutral ? (
              <Minus className="w-3.5 h-3.5" />
            ) : (
              <ArrowUpRight className="w-3.5 h-3.5" />
            )}
            <span>{Math.abs(improvementPct)}%</span>
          </div>
        )}
      </div>
    </div>
  );
};
