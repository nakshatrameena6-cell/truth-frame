import React from 'react';
import { cn } from '../../lib/utils';

interface EvidenceBarProps {
  label: string;
  scorePercent: number;
  bias: 'synthetic' | 'human' | 'neutral';
  explanation: string;
  className?: string;
}

export const EvidenceBar: React.FC<EvidenceBarProps> = ({
  label,
  scorePercent,
  bias,
  explanation,
  className,
}) => {
  const safePercent = Math.min(100, Math.max(0, scorePercent));

  let barColor = 'bg-txt-muted';
  let badgeLabel = 'Neutral';
  let badgeStyle = 'bg-bg-surface-elevated text-txt-muted border-border-subtle';

  if (bias === 'synthetic') {
    barColor = 'bg-rose-500';
    badgeLabel = 'Synthetic indicator';
    badgeStyle = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
  } else if (bias === 'human') {
    barColor = 'bg-emerald-500';
    badgeLabel = 'Human speech indicator';
    badgeStyle = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
  }

  return (
    <div className={cn('space-y-2 p-3.5 rounded-lg bg-bg-surface-elevated border border-border-subtle', className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-txt-main">
          {label}
        </span>
        <div className="flex items-center gap-2">
          <span className={cn('text-[10px] font-mono px-2 py-0.5 rounded border', badgeStyle)}>
            {badgeLabel}
          </span>
          <span className="text-xs font-mono font-bold text-txt-main">
            {safePercent}%
          </span>
        </div>
      </div>

      {/* Progress Track */}
      <div className="w-full bg-bg-surface rounded-full h-2.5 overflow-hidden border border-border-subtle">
        <div
          className={cn('h-full rounded-full transition-all duration-700 ease-out', barColor)}
          style={{ width: `${safePercent}%` }}
        />
      </div>

      <p className="text-xs text-txt-muted leading-relaxed">
        {explanation}
      </p>
    </div>
  );
};
