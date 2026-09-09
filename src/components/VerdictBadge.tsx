import React from 'react';
import { Verdict } from '../types/api';
import { cn } from '../lib/utils';
import { CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react';

interface VerdictBadgeProps {
  verdict: Verdict | null | undefined;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

export const VerdictBadge: React.FC<VerdictBadgeProps> = ({
  verdict,
  size = 'md',
  showIcon = true,
  className,
}) => {
  if (!verdict) {
    return (
      <span className={cn('inline-flex items-center px-2 py-0.5 rounded font-mono text-xs text-txt-dim bg-bg-surface-elevated border border-border-subtle', className)}>
        Unclassified
      </span>
    );
  }

  const config = {
    consistent_with_human: {
      label: 'Consistent with Human Speech',
      shortLabel: 'Consistent with Human',
      badgeClass: 'bg-verdict-human-bg text-verdict-human border-verdict-human-border',
      Icon: CheckCircle2,
    },
    inconclusive: {
      label: 'Inconclusive',
      shortLabel: 'Inconclusive',
      badgeClass: 'bg-verdict-inconclusive-bg text-verdict-inconclusive border-verdict-inconclusive-border',
      Icon: AlertTriangle,
    },
    likely_synthetic: {
      label: 'Likely Synthetic',
      shortLabel: 'Likely Synthetic',
      badgeClass: 'bg-verdict-synthetic-bg text-verdict-synthetic border-verdict-synthetic-border',
      Icon: AlertCircle,
    },
  }[verdict];

  const sizeClasses = {
    sm: 'text-[11px] px-2 py-0.5 font-medium tracking-tight gap-1.5',
    md: 'text-xs px-2.5 py-1 font-semibold tracking-tight gap-1.5',
    lg: 'text-sm px-3.5 py-1.5 font-bold tracking-tight gap-2',
  }[size];

  const IconComponent = config.Icon;

  return (
    <span
      className={cn(
        'inline-flex items-center rounded border transition-colors select-none font-mono',
        config.badgeClass,
        sizeClasses,
        className
      )}
    >
      {showIcon && <IconComponent className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />}
      <span>{size === 'sm' ? config.shortLabel : config.label}</span>
    </span>
  );
};
