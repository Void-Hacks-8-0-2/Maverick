import React from 'react';

interface PageHeaderProps {
  category?: string;
  title: string;
  description?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  category,
  title,
  description,
  badge,
  actions
}) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 mb-6" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      <div>
        {category && (
          <div className="text-[10px] font-mono tracking-widest font-semibold uppercase mb-1" style={{ color: 'var(--accent)' }}>
            {category}
          </div>
        )}
        <div className="flex items-center gap-3">
          <h1 className="text-xl sm:text-2xl font-semibold tracking-tight font-sans" style={{ color: 'var(--text-primary)' }}>
            {title}
          </h1>
          {badge}
        </div>
        {description && (
          <p className="text-xs mt-1 max-w-3xl leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0">
          {actions}
        </div>
      )}
    </div>
  );
};
