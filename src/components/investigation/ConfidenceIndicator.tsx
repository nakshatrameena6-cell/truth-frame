import React from 'react';
import { InvestigationResult } from '../../types/investigation';
import { Info, Gauge } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ConfidenceIndicatorProps {
  result: InvestigationResult;
  confidencePercent: number | null;
  className?: string;
}

export const ConfidenceIndicator: React.FC<ConfidenceIndicatorProps> = ({
  result,
  confidencePercent,
  className,
}) => {
  // If inconclusive, PRD strictly requires: NEVER generate a fake probability or confidence!
  if (result === 'inconclusive' || confidencePercent === null) {
    return (
      <div
        className={cn(
          'p-4 rounded-lg border border-border-subtle bg-bg-surface flex items-center justify-between gap-4',
          className
        )}
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500 shrink-0">
            <Info className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-txt-muted font-mono">
              Assessment Confidence
            </h4>
            <p className="text-sm font-medium text-txt-main">
              Not evaluable (Confidence withheld)
            </p>
          </div>
        </div>

        <div className="text-right">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-xs font-mono text-amber-400">
            Signal Quality Insufficient
          </span>
          <p className="text-[11px] text-txt-dim mt-0.5">
            Abstention required under bank policy
          </p>
        </div>
      </div>
    );
  }

  // Active confidence level calculation
  const isSynthetic = result === 'likely_synthetic';
  const confidenceLevel =
    confidencePercent >= 85 ? 'High certainty' : confidencePercent >= 70 ? 'Moderate certainty' : 'Lower certainty';

  return (
    <div
      className={cn(
        'p-4 rounded-lg border border-border-subtle bg-bg-surface flex items-center justify-between gap-4',
        className
      )}
    >
      <div className="flex items-center gap-3">
        <div
          className={cn(
            'w-9 h-9 rounded-full flex items-center justify-center shrink-0 border',
            isSynthetic
              ? 'bg-rose-500/10 border-rose-500/20 text-rose-500'
              : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500'
          )}
        >
          <Gauge className="w-5 h-5" />
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-txt-muted font-mono">
            Confidence
          </h4>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-txt-main">
              {confidencePercent}%
            </span>
            <span className="text-xs text-txt-muted font-medium">
              confidence
            </span>
          </div>
        </div>
      </div>

      <div className="flex flex-col items-end">
        <div className="flex items-center gap-1.5">
          <span
            className={cn(
              'w-2 h-2 rounded-full',
              isSynthetic ? 'bg-rose-500' : 'bg-emerald-500'
            )}
          />
          <span className="text-xs font-semibold text-txt-main font-mono">
            {confidenceLevel}
          </span>
        </div>
        <div className="w-32 bg-bg-surface-elevated rounded-full h-1.5 mt-2 overflow-hidden border border-border-subtle">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-500',
              isSynthetic ? 'bg-rose-500' : 'bg-emerald-500'
            )}
            style={{ width: `${Math.min(100, Math.max(0, confidencePercent))}%` }}
          />
        </div>
      </div>
    </div>
  );
};
