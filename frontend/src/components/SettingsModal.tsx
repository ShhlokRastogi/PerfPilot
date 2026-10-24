import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { 
  Cpu, 
  Check, 
  X, 
  ShieldCheck, 
  Sliders,
  Server,
  Lock,
  AlertTriangle
} from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [selectedModel, setSelectedModel] = useState('groq/llama-3.1-8b-instant');
  const [fallbackModel, setFallbackModel] = useState('groq/llama-3.3-70b-versatile');
  const [mockMode, setMockMode] = useState(false);
  const [hasGroq, setHasGroq] = useState(false);
  const [hasOpenAI, setHasOpenAI] = useState(false);
  const [hasAnthropic, setHasAnthropic] = useState(false);
  const [hasGemini, setHasGemini] = useState(false);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      api.getLLMConfig().then((cfg) => {
        setSelectedModel(cfg.active_model);
        setFallbackModel(cfg.fallback_model);
        setMockMode(cfg.mock_mode);
        setHasGroq(cfg.has_groq_key);
        setHasOpenAI(cfg.has_openai_key);
        setHasAnthropic(cfg.has_anthropic_key);
        setHasGemini(cfg.has_gemini_key);
        if (cfg.available_models && cfg.available_models.length > 0) {
          setAvailableModels(cfg.available_models);
        }
      }).catch(console.error);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      await api.updateLLMConfig({
        model: selectedModel,
        fallback_model: fallbackModel,
        mock_mode: mockMode,
      });
      setMessage('AI configuration updated successfully!');
      setTimeout(() => setMessage(null), 3000);
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative text-slate-100">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3 border-b border-slate-800 pb-4 mb-5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-slate-950 font-bold">
            <Sliders className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-base text-slate-100">AI Model & Inference Configuration</h3>
            <p className="text-xs text-slate-400">Manage LLM models and inspect backend environment credentials</p>
          </div>
        </div>

        {message && (
          <div className={`p-3 rounded-lg text-xs mb-4 flex items-center gap-2 ${
            message.startsWith('Error') 
              ? 'bg-rose-500/10 border border-rose-500/30 text-rose-300' 
              : 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
          }`}>
            <span>{message}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-4 text-xs font-sans">
          {/* Server API Key Status Grid (Backend Only) */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-200 flex items-center gap-1.5 text-xs">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Backend Credentials Security
              </span>
              <span className="text-[10px] font-mono text-cyan-400 flex items-center gap-1">
                <Lock className="w-3 h-3" /> Server-side only
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              API keys reside exclusively in backend environment variables (<code className="text-slate-300">.env</code>) and are never exposed to or requested from the frontend browser.
            </p>

            <div className="grid grid-cols-2 gap-2 pt-1 font-mono text-[11px]">
              <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                <span className="text-slate-300">GROQ_API_KEY</span>
                {hasGroq ? (
                  <span className="text-emerald-400 font-bold text-[10px] bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">Active</span>
                ) : (
                  <span className="text-slate-500 text-[10px]">Not set</span>
                )}
              </div>

              <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                <span className="text-slate-300">OPENAI_API_KEY</span>
                {hasOpenAI ? (
                  <span className="text-emerald-400 font-bold text-[10px] bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">Active</span>
                ) : (
                  <span className="text-slate-500 text-[10px]">Not set</span>
                )}
              </div>

              <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                <span className="text-slate-300">ANTHROPIC_KEY</span>
                {hasAnthropic ? (
                  <span className="text-emerald-400 font-bold text-[10px] bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">Active</span>
                ) : (
                  <span className="text-slate-500 text-[10px]">Not set</span>
                )}
              </div>

              <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
                <span className="text-slate-300">GEMINI_API_KEY</span>
                {hasGemini ? (
                  <span className="text-emerald-400 font-bold text-[10px] bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">Active</span>
                ) : (
                  <span className="text-slate-500 text-[10px]">Not set</span>
                )}
              </div>
            </div>
          </div>

          {/* Primary Model Selector */}
          <div>
            <label className="font-medium text-slate-300 block mb-1.5 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              Primary AI Model
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
            >
              <optgroup label="Groq (Ultra-Fast Inference)">
                <option value="groq/openai/gpt-oss-120b">groq/openai/gpt-oss-120b (High-Performance 120B)</option>
                <option value="groq/qwen/qwen3.8-27b">groq/qwen/qwen3.8-27b (Fast 27B)</option>
                <option value="groq/llama-3.3-70b-versatile">groq/llama-3.3-70b-versatile</option>
                <option value="groq/llama-3.1-8b-instant">groq/llama-3.1-8b-instant</option>
                <option value="groq/mixtral-8x7b-32768">groq/mixtral-8x7b-32768</option>
              </optgroup>
              <optgroup label="OpenAI">
                <option value="gpt-4o">gpt-4o</option>
                <option value="gpt-4o-mini">gpt-4o-mini</option>
              </optgroup>
              <optgroup label="Anthropic">
                <option value="claude-3-5-sonnet-20241022">claude-3-5-sonnet-20241022</option>
              </optgroup>
              <optgroup label="Google Gemini">
                <option value="gemini/gemini-1.5-pro">gemini/gemini-1.5-pro</option>
                <option value="gemini/gemini-1.5-flash">gemini/gemini-1.5-flash</option>
              </optgroup>
            </select>
          </div>

          {/* Fallback Model Selector */}
          <div>
            <label className="font-medium text-slate-300 block mb-1.5 flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-indigo-400" />
              Fallback Model (Auto-Failover)
            </label>
            <select
              value={fallbackModel}
              onChange={(e) => setFallbackModel(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
            >
              <option value="groq/qwen/qwen3.8-27b">groq/qwen/qwen3.8-27b</option>
              <option value="groq/openai/gpt-oss-120b">groq/openai/gpt-oss-120b</option>
              <option value="groq/llama-3.3-70b-versatile">groq/llama-3.3-70b-versatile</option>
              <option value="gpt-4o-mini">gpt-4o-mini</option>
              <option value="gemini/gemini-1.5-flash">gemini/gemini-1.5-flash</option>
            </select>
          </div>

          {/* Offline Mode Toggle */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
            <div>
              <div className="font-medium text-slate-200">Offline Simulation Mode</div>
              <div className="text-[11px] text-slate-500">Run sandbox tests without calling external LLM providers</div>
            </div>
            <input
              type="checkbox"
              checked={mockMode}
              onChange={(e) => setMockMode(e.target.checked)}
              className="w-4 h-4 accent-cyan-500 rounded cursor-pointer"
            />
          </div>

          <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold shadow-lg shadow-cyan-600/20 transition-all flex items-center gap-1.5"
            >
              <Check className="w-3.5 h-3.5" />
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
