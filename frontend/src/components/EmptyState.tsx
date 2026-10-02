import React from 'react';
import { SearchX } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No records matched query',
  description = 'Try widening the time window, relaxing filter criteria, or checking account IDs.',
  action,
  icon
}) => {
  return (
    <div className="w-full flex flex-col items-center justify-center p-8 surface-l2 border-hairline rounded-xl text-center">
      <div className="p-3 bg-white/[0.04] border border-white/[0.06] rounded-full text-slate-400 mb-3">
        {icon || <SearchX className="w-5 h-5 text-slate-400" />}
      </div>
      <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
        {title}
      </h3>
      <p className="text-xs text-slate-400 mt-1 max-w-md leading-relaxed">
        {description}
      </p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
};
