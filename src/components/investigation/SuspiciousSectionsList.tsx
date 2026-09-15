import React from 'react';
import { SuspiciousSection } from '../../types/investigation';
import { AlertTriangle, Play, CheckCircle2 } from 'lucide-react';
import { cn } from '../../lib/utils';

interface SuspiciousSectionsListProps {
  sections: SuspiciousSection[];
  activeSectionId: string | null;
  onSelectSection: (section: SuspiciousSection) => void;
  className?: string;
}

export const SuspiciousSectionsList: React.FC<SuspiciousSectionsListProps> = ({
  sections,
  activeSectionId,
  onSelectSection,
  className,
}) => {
  if (sections.length === 0) {
    return (
      <div
        className={cn(
          'rounded-lg border border-border-subtle bg-bg-surface p-5 space-y-2',
          className
        )}
      >
        <div className="flex items-center gap-2 text-emerald-500 font-medium text-sm">
          <CheckCircle2 className="w-5 h-5" />
          <span>No Suspicious Sections Localized</span>
        </div>
        <p className="text-xs text-txt-muted">
          Continuous vocal analysis did not detect localized synthetic anomalies or voice cloning splices across the recording timeline.
        </p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'rounded-lg border border-border-subtle bg-bg-surface p-5 space-y-4 shadow-sm',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-500" />
          <h3 className="text-sm font-semibold text-txt-main tracking-tight">
            Suspicious Sections ({sections.length})
          </h3>
        </div>
        <span className="text-[11px] text-txt-dim font-mono">
          Click any section to jump and listen
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {sections.map((sec, idx) => {
          const isActive = activeSectionId === sec.id;

          return (
            <div
              key={sec.id}
              onClick={() => onSelectSection(sec)}
              className={cn(
                'group p-3.5 rounded-lg border text-left cursor-pointer transition-all relative overflow-hidden',
                isActive
                  ? 'bg-rose-500/10 border-rose-500/80 ring-1 ring-rose-500/50 shadow-sm'
                  : 'bg-bg-surface-elevated border-border-subtle hover:border-rose-500/40 hover:bg-bg-surface-hover'
              )}
              role="button"
              tabIndex={0}
              aria-label={`Jump to suspicious section from ${sec.startFormatted} to ${sec.endFormatted} with ${sec.confidencePercent}% confidence`}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectSection(sec);
                }
              }}
            >
              {/* Left active marker bar */}
              <div
                className={cn(
                  'absolute top-0 bottom-0 left-0 w-1 transition-colors',
                  isActive ? 'bg-rose-500' : 'bg-transparent group-hover:bg-rose-400'
                )}
              />

              <div className="flex items-start justify-between gap-2">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-txt-main">
                      {sec.startFormatted} – {sec.endFormatted}
                    </span>
                    <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-bg-surface text-txt-dim border border-border-subtle">
                      Segment #{idx + 1}
                    </span>
                  </div>

                  <p className="text-xs text-txt-muted line-clamp-2">
                    {sec.evidenceSummary || 'Acoustic anomaly detected in voice pattern'}
                  </p>
                </div>

                {/* Confidence Badge */}
                <div className="text-right shrink-0">
                  <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-rose-500/15 border border-rose-500/30 text-rose-400 text-xs font-mono font-bold">
                    <span>{sec.confidencePercent}%</span>
                  </div>
                  <div className="text-[10px] text-txt-dim font-mono mt-0.5">
                    confidence
                  </div>
                </div>
              </div>

              {/* Action trigger label */}
              <div className="mt-2.5 pt-2 border-t border-border-subtle/50 flex items-center justify-between text-[11px] font-mono text-txt-muted group-hover:text-txt-main">
                <span className="flex items-center gap-1 text-rose-400">
                  <Play className="w-3 h-3 fill-rose-400" />
                  <span>Jump audio to {sec.startFormatted}</span>
                </span>
                {isActive && (
                  <span className="text-rose-500 font-semibold">Active Selection</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
