import React from 'react';

interface RiskBadgeProps {
  score?: number | null;
  band?: string | null;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  score,
  band,
  size = 'md',
  showLabel = true
}) => {
  const normalizedBand = (band || (score !== undefined && score !== null ? (
    score >= 85 ? 'VERY_HIGH' :
    score >= 70 ? 'HIGH' :
    score >= 40 ? 'MODERATE' : 'LOW'
  ) : 'LOW')).toUpperCase();

  const bandConfigs: Record<string, { bg: string; border: string; text: string; dot: string; label: string }> = {
    VERY_HIGH: {
      bg: 'bg-rose-950/30',
      border: 'border-rose-500/30',
      text: 'text-rose-400',
      dot: 'bg-rose-400',
      label: 'VERY HIGH RISK'
    },
    HIGH: {
      bg: 'bg-rose-950/25',
      border: 'border-rose-500/25',
      text: 'text-rose-300',
      dot: 'bg-rose-400',
      label: 'HIGH RISK'
    },
    MODERATE: {
      bg: 'bg-amber-950/30',
      border: 'border-amber-500/30',
      text: 'text-amber-400',
      dot: 'bg-amber-400',
      label: 'MODERATE RISK'
    },
    LOW: {
      bg: 'bg-emerald-950/25',
      border: 'border-emerald-500/30',
      text: 'text-emerald-400',
      dot: 'bg-emerald-400',
      label: 'LOW RISK'
    }
  };

  const config = bandConfigs[normalizedBand] || bandConfigs.LOW;

  const sizeClasses = {
    sm: 'text-[10px] px-1.5 py-0.5 font-mono',
    md: 'text-xs px-2 py-0.5 font-mono',
    lg: 'text-sm px-3 py-1 font-mono'
  };

  return (
    <span
      title="Step 5B Mule Risk Index (0-100 deterministic indicator)"
      className={`inline-flex items-center gap-1.5 rounded border font-medium ${config.bg} ${config.border} ${config.text} ${sizeClasses[size]}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      {score !== undefined && score !== null && (
        <span className="font-semibold">{score.toFixed(score % 1 === 0 ? 0 : 1)}</span>
      )}
      {showLabel && (
        <span className="tracking-wide text-[10px] opacity-90">{config.label}</span>
      )}
    </span>
  );
};
