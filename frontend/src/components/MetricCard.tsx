import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: LucideIcon;
  iconColor?: string;
  badge?: React.ReactNode;
  variant?: 'default' | 'cyan' | 'purple' | 'amber' | 'emerald' | 'rose';
  onClick?: () => void;
}

const variantStyles = {
  default: 'border-slate-200 bg-white shadow-xs',
  cyan: 'border-slate-200 bg-white shadow-xs',
  purple: 'border-violet-200 bg-white shadow-xs',
  amber: 'border-amber-200 bg-white shadow-xs',
  emerald: 'border-emerald-200 bg-white shadow-xs',
  rose: 'border-rose-200 bg-white shadow-xs',
};

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtitle,
  icon: Icon,
  iconColor = 'text-violet-600',
  badge,
  variant = 'default',
  onClick
}) => {
  return (
    <div
      onClick={onClick}
      className={`border rounded-lg p-4 sm:p-4.5 flex flex-col justify-between transition-all ${variantStyles[variant]} ${
        onClick ? 'cursor-pointer hover:border-violet-400 hover:shadow-sm' : ''
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
          {label}
        </span>
        <div className="flex items-center gap-1.5">
          {badge}
          {Icon && <Icon className={`w-3.5 h-3.5 ${iconColor}`} />}
        </div>
      </div>
      <div>
        <div className="text-xl sm:text-2xl font-semibold font-mono text-slate-900 tracking-tight tabular-nums">
          {value}
        </div>
        {subtitle && (
          <div className="text-[10px] font-mono text-slate-500 mt-1">
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
};
