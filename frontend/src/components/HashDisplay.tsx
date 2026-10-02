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
    <div
      className="inline-flex items-center gap-1.5 rounded px-2 py-0.5 group"
      style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-medium)' }}
    >
      {label && <span className="text-[9px] font-mono uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>{label}:</span>}
      <span
        title={hash}
        className={`font-mono font-medium select-all cursor-text ${monoClass}`}
        style={{ color: 'var(--accent)' }}
      >
        {display}
      </span>
      <button
        type="button"
        onClick={handleCopy}
        title="Copy complete SHA-256 hash to clipboard"
        className="p-0.5 transition-colors focus:outline-none"
        style={{ color: 'var(--text-secondary)' }}
      >
        {copied ? (
          <Check className="w-3 h-3 text-emerald-600" />
        ) : (
          <Copy className="w-3 h-3 opacity-60 group-hover:opacity-100" />
        )}
      </button>
    </div>
  );
};
