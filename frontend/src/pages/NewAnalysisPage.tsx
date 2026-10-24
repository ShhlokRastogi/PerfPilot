import React, { useState } from 'react';
import { api } from '../api/client';
import { PersonaConfig } from '../types';
import { 
  Play, 
  Server, 
  Gauge, 
  Sliders, 
  AlertCircle,
  Users,
  Plus,
  Trash2,
  Shield,
  Layers
} from 'lucide-react';

interface NewAnalysisPageProps {
  onRunStarted: (runId: string) => void;
}

export const NewAnalysisPage: React.FC<NewAnalysisPageProps> = ({ onRunStarted }) => {
  const [targetType, setTargetType] = useState<'custom' | 'staging'>('custom');
  const [repoPath, setRepoPath] = useState('demo-app');
  const [endpointPath, setEndpointPath] = useState('/api/products');
  const [useExternalServer, setUseExternalServer] = useState(false);
  const [externalUrl, setExternalUrl] = useState('http://localhost:8001');

  // Objectives
  const [p95LatencyMs, setP95LatencyMs] = useState(200);
  const [minSpeedupFactor, setMinSpeedupFactor] = useState(1.5);
  const [maxErrorRatePct, setMaxErrorRatePct] = useState(1.0);

  // Workload
  const [vus, setVus] = useState(10);
  const [durationSec, setDurationSec] = useState(10);

  // Multi-Role Personas (Kept on halt per architectural configuration; single heavy-workload prioritized)
  const [enablePersonas, setEnablePersonas] = useState(false);
  const [personas, setPersonas] = useState<PersonaConfig[]>([
    { role: 'critical_workload', traffic_pct: 100, path: '', headers: {} },
  ]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalTrafficPct = personas.reduce((acc, p) => acc + (Number(p.traffic_pct) || 0), 0);

  const handleAddPersona = () => {
    setPersonas([
      ...personas,
      { role: `role_${personas.length + 1}`, traffic_pct: 0, path: '', headers: {} }
    ]);
  };

  const handleRemovePersona = (index: number) => {
    setPersonas(personas.filter((_, i) => i !== index));
  };

  const handleUpdatePersona = (index: number, field: keyof PersonaConfig, value: any) => {
    const updated = [...personas];
    updated[index] = { ...updated[index], [field]: value };
    setPersonas(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (enablePersonas && personas.length > 0 && totalTrafficPct !== 100) {
      setError(`Multi-role traffic allocation must sum to 100% (currently ${totalTrafficPct}%). Please adjust persona weights.`);
      setLoading(false);
      return;
    }

    try {
      const finalTargetUrl = useExternalServer ? externalUrl : (endpointPath.startsWith('/') ? endpointPath : `/${endpointPath}`);
      const run = await api.createRun({
        target_type: targetType,
        target_url: finalTargetUrl,
        repo_path: repoPath,
        personas: enablePersonas ? personas : [],
        objectives: {
          p95_latency_ms: Number(p95LatencyMs),
          min_speedup_factor: Number(minSpeedupFactor),
          max_error_rate_pct: Number(maxErrorRatePct),
        },
        workload_config: {
          vus: Number(vus),
          duration_sec: Number(durationSec),
        },
      });

      onRunStarted(run.id);
    } catch (err: any) {
      setError(err.message || 'Failed to initialize analysis run');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">
          Configure Performance Analysis
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Specify target endpoints, multi-role user traffic personas, and performance SLAs.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Target Selection */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-5">
          <div className="flex items-center gap-2 font-semibold text-slate-200 text-sm border-b border-slate-800 pb-3">
            <Server className="w-4 h-4 text-cyan-400" />
            <span>Target Application & Auto-Sandbox Environment</span>
          </div>

          <div className="p-3.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs flex items-start gap-2.5">
            <Shield className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-cyan-200">Zero-Config Sandbox Execution:</span>
              <p className="text-slate-300 text-[11px] mt-0.5 leading-relaxed">
                You do NOT need to run your project on localhost. PerfPilot auto-detects your application (FastAPI, Flask, Express, static), boots it in an isolated baseline sandbox, streams server logs, and verifies candidate speedup in a disposable candidate sandbox.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Target Type
              </label>
              <select
                value={targetType}
                onChange={(e) => setTargetType(e.target.value as any)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="custom">Application API Server (Backend / REST)</option>
                <option value="staging">Full Web Application (HTML / Browser)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Repository / Codebase Directory Path
              </label>
              <input
                type="text"
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                placeholder="e.g. demo-app or ./src"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Endpoint Route Path to Benchmark
            </label>
            <input
              type="text"
              value={endpointPath}
              onChange={(e) => setEndpointPath(e.target.value)}
              placeholder="e.g. /api/products or /"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
              required
            />
            <p className="text-[11px] text-slate-500 mt-1">
              The application will be auto-launched on an isolated port and tested at this route path.
            </p>
          </div>

          {/* Optional External Host Override */}
          <div className="pt-2 border-t border-slate-800/80">
            <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={useExternalServer}
                onChange={(e) => setUseExternalServer(e.target.checked)}
                className="w-3.5 h-3.5 accent-cyan-500 rounded"
              />
              <span>Manually override with an already-running external server URL (optional)</span>
            </label>

            {useExternalServer && (
              <div className="mt-3">
                <input
                  type="url"
                  value={externalUrl}
                  onChange={(e) => setExternalUrl(e.target.value)}
                  placeholder="http://localhost:8001"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  When enabled, PerfPilot targets this external URL instead of auto-booting the local sandbox.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Multi-Role Personas (Item 7) */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2 font-semibold text-slate-200 text-sm">
              <Users className="w-4 h-4 text-sky-400" />
              <span>Multi-Role Workload Simulation (Personas)</span>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-xs font-mono px-2 py-0.5 rounded border ${
                totalTrafficPct === 100 
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
              }`}>
                Traffic Total: {totalTrafficPct}%
              </span>
              <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enablePersonas}
                  onChange={(e) => setEnablePersonas(e.target.checked)}
                  className="w-3.5 h-3.5 accent-cyan-500 rounded"
                />
                Enable Personas
              </label>
            </div>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            Multi-role splitting is currently on hold. Focus is concentrated on the primary dynamic endpoint under heavy concurrency.
          </p>

          {enablePersonas && (
            <div className="space-y-3 pt-2">
              <div className="grid grid-cols-12 gap-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-1">
                <div className="col-span-3">Role Identifier</div>
                <div className="col-span-2">Traffic %</div>
                <div className="col-span-6">Relative Path / Sub-Endpoint</div>
                <div className="col-span-1 text-center">Action</div>
              </div>

              {personas.map((persona, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2 items-center bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                  <div className="col-span-3">
                    <input
                      type="text"
                      value={persona.role}
                      onChange={(e) => handleUpdatePersona(idx, 'role', e.target.value)}
                      placeholder="e.g. heavy_workload"
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div className="col-span-2">
                    <div className="relative">
                      <input
                        type="number"
                        min={1}
                        max={100}
                        value={persona.traffic_pct}
                        onChange={(e) => handleUpdatePersona(idx, 'traffic_pct', Number(e.target.value))}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono pr-6 focus:outline-none focus:border-cyan-500"
                      />
                      <span className="absolute right-2 top-1.5 text-[10px] text-slate-500">%</span>
                    </div>
                  </div>
                  <div className="col-span-6">
                    <input
                      type="text"
                      value={persona.path}
                      onChange={(e) => handleUpdatePersona(idx, 'path', e.target.value)}
                      placeholder="e.g. /api/search or /submit"
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div className="col-span-1 text-center">
                    {personas.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemovePersona(idx)}
                        className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                        title="Remove role"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}

              <button
                type="button"
                onClick={handleAddPersona}
                className="flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-medium px-2 py-1 mt-1"
              >
                <Plus className="w-3.5 h-3.5" />
                Add User Role Persona
              </button>
            </div>
          )}
        </div>

        {/* Performance Objectives (SLAs) */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2 font-semibold text-slate-200 text-sm border-b border-slate-800 pb-3">
            <Gauge className="w-4 h-4 text-emerald-400" />
            <span>Target Performance Objectives</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Max p95 Latency Objective
              </label>
              <div className="relative">
                <input
                  type="number"
                  value={p95LatencyMs}
                  onChange={(e) => setP95LatencyMs(Number(e.target.value))}
                  min={1}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono pr-8 focus:outline-none focus:border-cyan-500"
                />
                <span className="absolute right-3 top-2 text-xs text-slate-500">ms</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Minimum Speedup Factor
              </label>
              <div className="relative">
                <input
                  type="number"
                  step="0.1"
                  value={minSpeedupFactor}
                  onChange={(e) => setMinSpeedupFactor(Number(e.target.value))}
                  min={1.0}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono pr-8 focus:outline-none focus:border-cyan-500"
                />
                <span className="absolute right-3 top-2 text-xs text-slate-500">x</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Max Allowed Error Rate
              </label>
              <div className="relative">
                <input
                  type="number"
                  step="0.1"
                  value={maxErrorRatePct}
                  onChange={(e) => setMaxErrorRatePct(Number(e.target.value))}
                  min={0.0}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono pr-8 focus:outline-none focus:border-cyan-500"
                />
                <span className="absolute right-3 top-2 text-xs text-slate-500">%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Load Test Parameters */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2 font-semibold text-slate-200 text-sm border-b border-slate-800 pb-3">
            <Sliders className="w-4 h-4 text-purple-400" />
            <span>Load Workload Configuration (k6 Engine)</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Virtual Users (VUs)
              </label>
              <input
                type="number"
                value={vus}
                onChange={(e) => setVus(Number(e.target.value))}
                min={1}
                max={100}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
              />
              <p className="text-[11px] text-slate-500 mt-1">Concurrency intensity</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Benchmark Duration
              </label>
              <div className="relative">
                <input
                  type="number"
                  value={durationSec}
                  onChange={(e) => setDurationSec(Number(e.target.value))}
                  min={2}
                  max={60}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono pr-8 focus:outline-none focus:border-cyan-500"
                />
                <span className="absolute right-3 top-2 text-xs text-slate-500">sec</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1">Duration of load test execution</p>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white text-sm font-bold shadow-xl shadow-cyan-600/20 transition-all disabled:opacity-50"
          >
            <Play className="w-4 h-4 fill-white" />
            {loading ? 'Initializing Pipeline...' : 'Launch PerfPilot Analysis'}
          </button>
        </div>
      </form>
    </div>
  );
};
