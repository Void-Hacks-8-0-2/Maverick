import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  submessage?: string;
  heightClass?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Executing forensic query...',
  submessage = 'Retrieving analytical data from production store',
  heightClass = 'h-48'
}) => {
  return (
    <div className={`w-full flex flex-col items-center justify-center surface-l2 border-hairline rounded-xl p-6 ${heightClass}`}>
      <div className="flex items-center space-x-3 text-cyan-400">
        <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
        <span className="text-xs font-mono font-medium text-slate-200 tracking-tight">
          {message}
        </span>
      </div>
      {submessage && (
        <p className="text-[11px] font-mono text-slate-500 mt-2 text-center max-w-sm">
          {submessage}
        </p>
      )}
    </div>
  );
};
