import React from 'react';
import { EvidenceCategory } from '../../types/investigation';
import { EvidenceBar } from './EvidenceBar';
import { HelpCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

interface EvidencePanelProps {
  categories: EvidenceCategory[];
  className?: string;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  categories,
  className,
}) => {
  return (
    <div
      className={cn(
        'rounded-lg border border-border-subtle bg-bg-surface p-5 space-y-4 shadow-sm',
        className
      )}
    >
      <div className="flex items-center justify-between border-b border-border-subtle pb-3">
        <div className="space-y-0.5">
          <h3 className="text-sm font-semibold text-txt-main tracking-tight">
            Why this result?
          </h3>
          <p className="text-xs text-txt-muted">
            Evaluation of acoustic evidence across core forensic speech dimensions
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-txt-dim font-mono">
          <HelpCircle className="w-3.5 h-3.5" />
          <span>Analyst Evidence Breakdown</span>
        </div>
      </div>

      <div className="space-y-3">
        {categories.map((cat) => (
          <EvidenceBar
            key={cat.id || cat.name}
            label={cat.name}
            scorePercent={cat.scorePercent}
            bias={cat.bias}
            explanation={cat.explanation}
          />
        ))}
      </div>
    </div>
  );
};
