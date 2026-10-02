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
    <div className="w-full flex flex-col items-center justify-center p-8 rounded-xl text-center" style={{ backgroundColor: '#ffffff', border: '1px solid var(--border-subtle)' }}>
      <div className="p-3 rounded-full mb-3" style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-medium)', color: 'var(--text-secondary)' }}>
        {icon || <SearchX className="w-5 h-5" style={{ color: 'var(--text-secondary)' }} />}
      </div>
      <h3 className="text-xs font-mono font-semibold uppercase tracking-wider" style={{ color: 'var(--text-primary)' }}>
        {title}
      </h3>
      <p className="text-xs mt-1 max-w-md leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {description}
      </p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
};
