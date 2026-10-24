import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { SettingsModal } from './components/SettingsModal';
import { OverviewPage } from './pages/OverviewPage';
import { NewAnalysisPage } from './pages/NewAnalysisPage';
import { RunDetailsPage } from './pages/RunDetailsPage';

export function App() {
  const [currentTab, setCurrentTab] = useState<'overview' | 'new-analysis' | 'run-details' | 'audit'>('overview');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);

  const handleSelectRun = (runId: string) => {
    setSelectedRunId(runId);
    setCurrentTab('run-details');
  };

  const handleRunStarted = (runId: string) => {
    setSelectedRunId(runId);
    setCurrentTab('run-details');
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col font-sans">
      <Navbar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        selectedRunId={selectedRunId}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentTab === 'overview' && (
          <OverviewPage
            onSelectRun={handleSelectRun}
            onNewAnalysis={() => setCurrentTab('new-analysis')}
          />
        )}

        {currentTab === 'new-analysis' && (
          <NewAnalysisPage onRunStarted={handleRunStarted} />
        )}

        {currentTab === 'run-details' && selectedRunId && (
          <RunDetailsPage
            runId={selectedRunId}
            onBack={() => setCurrentTab('overview')}
          />
        )}
      </main>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />

      <footer className="border-t border-slate-900 bg-[#090d16] py-6 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 flex items-center justify-between">
          <span>PerfPilot © 2026 AgentOps Hackathon</span>
          <span>FastAPI • LiteLLM • k6 • Playwright • Docker</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
