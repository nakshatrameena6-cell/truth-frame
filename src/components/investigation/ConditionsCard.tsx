import React, { useState } from 'react';
import { RecordingConditions } from '../../types/investigation';
import { Sliders, ChevronDown, ChevronUp, Activity } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ConditionsCardProps {
  conditions: RecordingConditions;
  className?: string;
}

export const ConditionsCard: React.FC<ConditionsCardProps> = ({
  conditions,
  className,
}) => {
  const [showDetails, setShowDetails] = useState(false);

  const getQualityBadge = (quality: string) => {
    switch (quality) {
      case 'Good':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'Moderate':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'Degraded':
      case 'Limited':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      default:
        return 'bg-bg-surface-elevated text-txt-muted border-border-subtle';
    }
  };

  return (
    <div
      className={cn(
        'rounded-lg border border-border-subtle bg-bg-surface p-5 space-y-4 shadow-sm',
        className
      )}
    >
      <div className="flex items-center justify-between border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-brand" />
          <h3 className="text-sm font-semibold text-txt-main tracking-tight">
            Recording Conditions
          </h3>
        </div>
        <span className="text-[11px] font-mono text-txt-dim">
          Acoustic Environment
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Audio Quality */}
        <div className="p-3 rounded-lg bg-bg-surface-elevated border border-border-subtle space-y-1">
          <span className="text-[11px] font-mono text-txt-muted uppercase">
            Audio quality
          </span>
          <div>
            <span
              className={cn(
                'inline-block text-xs font-mono font-semibold px-2 py-0.5 rounded border',
                getQualityBadge(conditions.overallQuality)
              )}
            >
              {conditions.overallQuality}
            </span>
          </div>
        </div>

        {/* Speech available */}
        <div className="p-3 rounded-lg bg-bg-surface-elevated border border-border-subtle space-y-1">
          <span className="text-[11px] font-mono text-txt-muted uppercase">
            Speech available
          </span>
          <div className="text-sm font-semibold font-mono text-txt-main">
            {conditions.speechAvailableDuration}
          </div>
        </div>

        {/* Clarity */}
        <div className="p-3 rounded-lg bg-bg-surface-elevated border border-border-subtle space-y-1">
          <span className="text-[11px] font-mono text-txt-muted uppercase">
            Clarity
          </span>
          <div className="text-sm font-semibold font-mono text-txt-main">
            {conditions.clarity}
          </div>
        </div>

        {/* Recording type */}
        <div className="p-3 rounded-lg bg-bg-surface-elevated border border-border-subtle space-y-1">
          <span className="text-[11px] font-mono text-txt-muted uppercase">
            Recording type
          </span>
          <div className="text-sm font-semibold font-mono text-txt-main">
            {conditions.recordingType}
          </div>
        </div>
      </div>

      {conditions.notes && (
        <p className="text-xs text-txt-muted bg-bg-surface-elevated/50 p-2.5 rounded border border-border-subtle">
          <span className="font-semibold text-txt-main">Forensic Note: </span>
          {conditions.notes}
        </p>
      )}

      {/* Expandable technical details button */}
      <div className="pt-1">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="flex items-center gap-1.5 text-xs font-mono text-txt-muted hover:text-txt-main transition-colors"
          aria-expanded={showDetails}
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>
            {showDetails ? 'Hide additional recording details' : 'View additional recording details'}
          </span>
          {showDetails ? (
            <ChevronUp className="w-3.5 h-3.5 ml-0.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 ml-0.5" />
          )}
        </button>

        {showDetails && (
          <div className="mt-3 p-3.5 rounded-lg bg-bg-surface-elevated border border-border-subtle text-xs font-mono space-y-2 text-txt-muted animate-in fade-in duration-150">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div>
                <span className="text-txt-dim block text-[10px] uppercase">Format Container</span>
                <span className="text-txt-main font-semibold">{conditions.format}</span>
              </div>
              <div>
                <span className="text-txt-dim block text-[10px] uppercase">Sampling Rate</span>
                <span className="text-txt-main font-semibold">{conditions.sampleRateFormatted}</span>
              </div>
              <div>
                <span className="text-txt-dim block text-[10px] uppercase">Channel Config</span>
                <span className="text-txt-main font-semibold">{conditions.channelsFormatted}</span>
              </div>
            </div>
            <p className="text-[11px] text-txt-dim pt-2 border-t border-border-subtle">
              Recording conditions establish the evidentiary baseline. High noise or heavy telecom compression mandates careful corroboration.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
