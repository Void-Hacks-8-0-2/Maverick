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
    <div className="w-full p-4 sm:p-5 bg-rose-50 border border-rose-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
        <div>
          <h4 className="text-xs font-semibold text-rose-900 uppercase tracking-wider">
            {title}
          </h4>
          <p className="text-xs text-rose-700 mt-1 max-w-2xl font-mono leading-relaxed">
            {error}
          </p>
        </div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-rose-100 text-rose-700 border border-rose-300 rounded-lg text-xs font-medium transition shadow-sm shrink-0 self-start sm:self-auto"
        >
          <RefreshCw className="w-3 h-3" />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
};
