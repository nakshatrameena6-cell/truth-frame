import React from 'react';
import { InvestigationResult } from '../../types/investigation';
import { ShieldCheck, AlertTriangle, HelpCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

interface VerdictCardProps {
  result: InvestigationResult;
  className?: string;
}

export const VerdictCard: React.FC<VerdictCardProps> = ({ result, className }) => {
  if (result === 'likely_synthetic') {
    return (
      <div
        className={cn(
          'p-5 rounded-lg border-2 border-verdict-synthetic-border bg-verdict-synthetic-bg flex items-start gap-4 transition-all',
          className
        )}
        role="status"
        aria-label="Investigation result: Likely Synthetic"
      >
        <div className="p-2.5 rounded-md bg-rose-500/20 text-verdict-synthetic shrink-0">
          <AlertTriangle className="w-7 h-7" aria-hidden="true" />
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-rose-500 font-mono">
              Determination
            </span>
            <span className="text-[11px] px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 font-medium">
              High Risk
            </span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-txt-main">
            Likely Synthetic
          </h2>
          <p className="text-sm text-txt-muted leading-relaxed">
            The recording contains acoustic characteristics consistent with synthetic or cloned speech.
          </p>
        </div>
      </div>
    );
  }

  if (result === 'consistent_with_human') {
    return (
      <div
        className={cn(
          'p-5 rounded-lg border-2 border-verdict-human-border bg-verdict-human-bg flex items-start gap-4 transition-all',
          className
        )}
        role="status"
        aria-label="Investigation result: Consistent with Human"
      >
        <div className="p-2.5 rounded-md bg-emerald-500/20 text-verdict-human shrink-0">
          <ShieldCheck className="w-7 h-7" aria-hidden="true" />
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-500 font-mono">
              Determination
            </span>
            <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-medium">
              Authentic
            </span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-txt-main">
            Consistent with Human
          </h2>
          <p className="text-sm text-txt-muted leading-relaxed">
            The recording does not show sufficient evidence of synthetic speech.
          </p>
        </div>
      </div>
    );
  }

  // Inconclusive
  return (
    <div
      className={cn(
        'p-5 rounded-lg border-2 border-verdict-inconclusive-border bg-verdict-inconclusive-bg flex items-start gap-4 transition-all',
        className
      )}
      role="status"
      aria-label="Investigation result: Inconclusive"
    >
      <div className="p-2.5 rounded-md bg-amber-500/20 text-verdict-inconclusive shrink-0">
        <HelpCircle className="w-7 h-7" aria-hidden="true" />
      </div>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-amber-500 font-mono">
            Determination
          </span>
          <span className="text-[11px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-medium">
            Abstention
          </span>
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-txt-main">
          Inconclusive
        </h2>
        <p className="text-sm text-txt-muted leading-relaxed">
          A reliable determination could not be made. There isn't enough reliable audio information to make a dependable assessment.
        </p>
      </div>
    </div>
  );
};
