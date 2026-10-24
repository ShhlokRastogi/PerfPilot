import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { BenchmarkMetric } from '../types';

interface LatencyChartProps {
  baselineMetric?: BenchmarkMetric | null;
  candidateMetric?: BenchmarkMetric | null;
}

export const LatencyChart: React.FC<LatencyChartProps> = ({
  baselineMetric,
  candidateMetric,
}) => {
  if (!baselineMetric) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500 font-mono text-xs">
        No benchmark metrics recorded yet
      </div>
    );
  }

  const data = [
    {
      percentile: 'p50',
      Baseline: baselineMetric.p50_latency_ms,
      ...(candidateMetric ? { Candidate: candidateMetric.p50_latency_ms } : {}),
    },
    {
      percentile: 'p90',
      Baseline: baselineMetric.p90_latency_ms,
      ...(candidateMetric ? { Candidate: candidateMetric.p90_latency_ms } : {}),
    },
    {
      percentile: 'p95',
      Baseline: baselineMetric.p95_latency_ms,
      ...(candidateMetric ? { Candidate: candidateMetric.p95_latency_ms } : {}),
    },
    {
      percentile: 'p99',
      Baseline: baselineMetric.p99_latency_ms,
      ...(candidateMetric ? { Candidate: candidateMetric.p99_latency_ms } : {}),
    },
  ];

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis
            dataKey="percentile"
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 12, fontFamily: 'monospace' }}
          />
          <YAxis
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 12, fontFamily: 'monospace' }}
            unit="ms"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f172a',
              borderColor: '#334155',
              borderRadius: '8px',
              fontFamily: 'monospace',
              fontSize: '12px',
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: '12px', fontFamily: 'monospace', paddingTop: '8px' }}
          />
          <Bar dataKey="Baseline" fill="#f43f5e" radius={[4, 4, 0, 0]} name="Baseline (ms)" />
          {candidateMetric && (
            <Bar dataKey="Candidate" fill="#10b981" radius={[4, 4, 0, 0]} name="Candidate (ms)" />
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
