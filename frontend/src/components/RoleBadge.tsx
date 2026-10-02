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
  const normalized = role.toUpperCase();

  const configs: Record<string, { label: string; fullTitle: string; desc: string; style: string }> = {
    L1: {
      label: 'L1 COLLECTOR',
      fullTitle: 'Layer 1: Collector Mule Candidate',
      desc: 'High fan-in credit aggregation from multiple victim/counterparty accounts',
      style: 'bg-cyan-950/30 border-cyan-500/30 text-cyan-300'
    },
    L2: {
      label: 'L2 DISTRIBUTOR',
      fullTitle: 'Layer 2: Distributor Mule Candidate',
      desc: 'Rapid pass-through fan-out dispersion splitting funds to downstream layers',
      style: 'bg-purple-950/30 border-purple-500/30 text-purple-300'
    },
    L3: {
      label: 'L3 TERMINAL',
      fullTitle: 'Layer 3: Terminal / Cash-Out Candidate',
      desc: 'Sink node absorption, egress termination, or lack of forward distribution',
      style: 'bg-rose-950/30 border-rose-500/30 text-rose-300'
    },
    MIXED: {
      label: 'MULTI-ROLE',
      fullTitle: 'Multi-Role Candidate',
      desc: 'Exhibits simultaneous behavioral characteristics across multiple layers',
      style: 'bg-amber-950/30 border-amber-500/30 text-amber-300'
    }
  };

  const config = configs[normalized] || {
    label: normalized,
    fullTitle: normalized,
    desc: 'Investigative candidate role classification',
    style: 'bg-slate-900 border-white/[0.08] text-slate-300'
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
