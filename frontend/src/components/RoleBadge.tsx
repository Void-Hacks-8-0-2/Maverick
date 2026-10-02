import React from 'react';

interface RoleBadgeProps {
  role: 'L1' | 'L2' | 'L3' | 'MIXED' | string;
  size?: 'sm' | 'md';
  detailed?: boolean;
}

export const RoleBadge: React.FC<RoleBadgeProps> = ({
  role,
  size = 'md',
  detailed = false
}) => {
  const normalized = (role || '').toUpperCase();
  const key = normalized.includes('L3') ? 'L3' : normalized.includes('L2') ? 'L2' : normalized.includes('L1') ? 'L1' : normalized;

  const configs: Record<string, { label: string; fullTitle: string; desc: string; style: string }> = {
    L1: {
      label: 'L1 COLLECTOR',
      fullTitle: 'Layer 1: Collector Mule Candidate',
      desc: 'High fan-in credit aggregation from multiple victim/counterparty accounts',
      style: 'bg-emerald-50 border-emerald-300 text-emerald-700'
    },
    L2: {
      label: 'L2 DISTRIBUTOR',
      fullTitle: 'Layer 2: Distributor Mule Candidate',
      desc: 'Rapid pass-through fan-out dispersion splitting funds to downstream layers',
      style: 'bg-amber-50 border-amber-300 text-amber-700'
    },
    L3: {
      label: 'L3 TERMINAL',
      fullTitle: 'L3 Terminal Candidate',
      desc: 'Observed transaction indicators associated with terminal/cash-out behavior',
      style: 'bg-rose-50 border-rose-300 text-rose-700'
    },
    MIXED: {
      label: 'MULTI-ROLE',
      fullTitle: 'Multi-Role Candidate',
      desc: 'Exhibits simultaneous behavioral characteristics across multiple layers',
      style: 'bg-violet-50 border-violet-300 text-violet-700'
    }
  };

  const config = configs[key] || {
    label: normalized,
    fullTitle: normalized,
    desc: 'Investigative candidate role classification',
    style: 'bg-slate-100 border-slate-300 text-slate-700'
  };

  const sizeClasses = {
    sm: 'text-[10px] px-1.5 py-0.5 font-mono',
    md: 'text-xs px-2 py-0.5 font-mono'
  };

  return (
    <span
      title={`${config.fullTitle} — ${config.desc}`}
      className={`inline-flex items-center gap-1.5 rounded border font-medium cursor-help transition-opacity hover:opacity-90 ${config.style} ${sizeClasses[size]}`}
    >
      <span className="font-semibold tracking-wider text-[10px]">{detailed ? config.fullTitle : config.label}</span>
    </span>
  );
};
