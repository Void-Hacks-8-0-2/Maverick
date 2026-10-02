import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  error?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Investigation Query Failed',
  error = 'An analytical engine query error occurred while processing the request.',
  onRetry
}) => {
  return (
    <div className="w-full p-4 sm:p-5 surface-l2 border border-rose-500/20 bg-rose-500/5 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
        <div>
          <h4 className="text-xs font-mono font-semibold text-rose-300 uppercase tracking-wider">
            {title}
          </h4>
          <p className="text-xs text-slate-300 mt-1 max-w-2xl font-mono leading-relaxed">
            {error}
          </p>
        </div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-lg text-xs font-mono font-medium transition shrink-0 self-start sm:self-auto"
        >
          <RefreshCw className="w-3 h-3" />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
};
