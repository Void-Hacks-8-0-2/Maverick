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
      bg: 'bg-rose-50',
      border: 'border-rose-300',
      text: 'text-rose-700',
      dot: 'bg-rose-600',
      label: 'VERY HIGH RISK'
    },
    HIGH: {
      bg: 'bg-rose-50',
      border: 'border-rose-200',
      text: 'text-rose-600',
      dot: 'bg-rose-500',
      label: 'HIGH RISK'
    },
    MODERATE: {
      bg: 'bg-amber-50',
      border: 'border-amber-300',
      text: 'text-amber-700',
      dot: 'bg-amber-500',
      label: 'MODERATE RISK'
    },
    LOW: {
      bg: 'bg-emerald-50',
      border: 'border-emerald-300',
      text: 'text-emerald-700',
      dot: 'bg-emerald-500',
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
