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
  default: 'border-white/[0.06] bg-[#0b0f19]/70',
  cyan: 'border-cyan-500/20 bg-[#0b0f19]/70',
  purple: 'border-purple-500/20 bg-[#0b0f19]/70',
  amber: 'border-amber-500/20 bg-[#0b0f19]/70',
  emerald: 'border-emerald-500/20 bg-[#0b0f19]/70',
  rose: 'border-rose-500/20 bg-[#0b0f19]/70',
};

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtitle,
  icon: Icon,
  iconColor = 'text-cyan-400',
  badge,
  variant = 'default',
  onClick
}) => {
  return (
    <div
      onClick={onClick}
      className={`border rounded-lg p-4 sm:p-4.5 flex flex-col justify-between transition-all backdrop-blur-sm ${variantStyles[variant]} ${
        onClick ? 'cursor-pointer hover:border-cyan-500/40 hover:bg-[#0e1424]/80' : ''
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-medium">
          {label}
        </span>
        <div className="flex items-center gap-1.5">
          {badge}
          {Icon && <Icon className={`w-3.5 h-3.5 ${iconColor}`} />}
        </div>
      </div>
      <div>
        <div className="text-xl sm:text-2xl font-semibold font-mono text-slate-100 tracking-tight tabular-nums">
          {value}
        </div>
        {subtitle && (
          <div className="text-[10px] font-mono text-slate-400 mt-1">
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
};
