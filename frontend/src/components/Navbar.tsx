import React, { useEffect, useState } from 'react';
import { Activity, Shield, Zap, Terminal, CheckCircle2, AlertCircle, Key, Sliders } from 'lucide-react';
import { api } from '../api/client';

interface NavbarProps {
  currentTab: 'overview' | 'new-analysis' | 'run-details' | 'audit';
  setCurrentTab: (tab: 'overview' | 'new-analysis' | 'run-details' | 'audit') => void;
  selectedRunId?: string | null;
  onOpenSettings: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, setCurrentTab, selectedRunId, onOpenSettings }) => {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    api.getHealth()
      .then(() => setHealthy(true))
      .catch(() => setHealthy(false));
  }, []);

  return (
    <header className="sticky top-0 z-50 bg-[#0f172a]/95 backdrop-blur border-b border-slate-800 text-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => setCurrentTab('overview')}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-300 bg-clip-text text-transparent">
                PerfPilot
              </span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-cyan-950/80 text-cyan-400 border border-cyan-800/50">
                AgentOps 2026
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">Autonomous Performance Engineering</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-slate-900/60 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setCurrentTab('overview')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              currentTab === 'overview'
                ? 'bg-slate-800 text-cyan-300 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setCurrentTab('new-analysis')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              currentTab === 'new-analysis'
                ? 'bg-slate-800 text-cyan-300 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            + New Analysis
          </button>
          {selectedRunId && (
            <button
              onClick={() => setCurrentTab('run-details')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
                currentTab === 'run-details'
                  ? 'bg-slate-800 text-cyan-300 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Activity className="w-3 h-3 text-cyan-400" />
              Active Run
            </button>
          )}
        </nav>

        {/* System Health & Settings */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenSettings}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-xs text-slate-300 hover:text-white transition-all shadow-sm"
            title="Configure AI Models and System Settings"
          >
            <Sliders className="w-3.5 h-3.5 text-cyan-400" />
            <span className="font-medium hidden sm:inline">AI Model Settings</span>
          </button>

          <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
            {healthy === true ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-slate-300 font-mono text-[11px]">Backend Ready</span>
              </>
            ) : healthy === false ? (
              <>
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                <span className="text-rose-400 font-mono text-[11px]">Backend Offline</span>
              </>
            ) : (
              <span className="text-slate-500 font-mono text-[11px]">Connecting...</span>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
