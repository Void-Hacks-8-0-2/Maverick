import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface HashDisplayProps {
  hash: string;
  label?: string;
  truncateLength?: number;
  monoClass?: string;
}

export const HashDisplay: React.FC<HashDisplayProps> = ({
  hash,
  label,
  truncateLength = 14,
  monoClass = 'text-xs'
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const display = hash && hash.length > truncateLength
    ? `${hash.substring(0, truncateLength)}...`
    : hash;

  return (
    <div className="inline-flex items-center gap-1.5 bg-[#06080d]/80 border border-white/[0.08] rounded px-2 py-0.5 group">
      {label && <span className="text-[9px] font-mono text-slate-400 uppercase tracking-wider">{label}:</span>}
      <span
        title={hash}
        className={`font-mono text-cyan-300 select-all cursor-text ${monoClass}`}
      >
        {display}
      </span>
      <button
        type="button"
        onClick={handleCopy}
        title="Copy complete SHA-256 hash to clipboard"
        className="text-slate-400 hover:text-cyan-300 p-0.5 transition-colors focus:outline-none"
      >
        {copied ? (
          <Check className="w-3 h-3 text-emerald-400" />
        ) : (
          <Copy className="w-3 h-3 opacity-60 group-hover:opacity-100" />
        )}
      </button>
    </div>
  );
};
