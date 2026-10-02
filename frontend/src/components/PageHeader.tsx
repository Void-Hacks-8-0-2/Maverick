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
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 mb-6 border-b border-white/[0.06]">
      <div>
        {category && (
          <div className="text-[10px] font-mono tracking-widest text-cyan-400 uppercase mb-1">
            {category}
          </div>
        )}
        <div className="flex items-center gap-3">
          <h1 className="text-xl sm:text-2xl font-semibold text-slate-100 tracking-tight font-sans">
            {title}
          </h1>
          {badge}
        </div>
        {description && (
          <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
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
