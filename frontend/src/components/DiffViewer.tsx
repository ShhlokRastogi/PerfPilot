import React from 'react';
import { FileCode, Copy, Check } from 'lucide-react';

interface DiffViewerProps {
  diff: string;
  affectedFiles?: string[];
  patchHash?: string;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({
  diff,
  affectedFiles = [],
  patchHash,
}) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(diff);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = diff.split('\n');

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/90 overflow-hidden font-mono text-xs">
      {/* Diff Header */}
      <div className="bg-slate-900 px-4 py-2.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold text-slate-200">
            {affectedFiles.length > 0 ? affectedFiles.join(', ') : 'Proposed Optimization Patch'}
          </span>
          {patchHash && (
            <span className="ml-2 px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700/60" title={`SHA-256: ${patchHash}`}>
              SHA: {patchHash.substring(0, 10)}...
            </span>
          )}
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          <span>{copied ? 'Copied' : 'Copy Diff'}</span>
        </button>
      </div>

      {/* Diff Code View */}
      <div className="p-3 overflow-x-auto max-h-96">
        {lines.map((line, idx) => {
          let lineClass = 'text-slate-300';
          let bgClass = '';
          if (line.startsWith('+') && !line.startsWith('+++')) {
            lineClass = 'text-emerald-400 font-medium';
            bgClass = 'bg-emerald-950/30';
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            lineClass = 'text-rose-400 font-medium';
            bgClass = 'bg-rose-950/30';
          } else if (line.startsWith('@@')) {
            lineClass = 'text-indigo-400 font-bold';
            bgClass = 'bg-indigo-950/20';
          }

          return (
            <div key={idx} className={`flex items-start gap-3 py-0.5 px-2 rounded-sm ${bgClass}`}>
              <span className="w-8 select-none text-slate-600 text-right">{idx + 1}</span>
              <pre className={`flex-1 m-0 overflow-visible whitespace-pre-wrap ${lineClass}`}>
                {line || ' '}
              </pre>
            </div>
          );
        })}
      </div>
    </div>
  );
};
