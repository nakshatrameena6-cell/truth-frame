import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Cpu, Activity, Info, FileCheck, Layers } from 'lucide-react';
import { EvidencePayload } from '../../types/api';
import { cn } from '../../lib/utils';

interface EvidenceDrawerProps {
  evidence: EvidencePayload | null | undefined;
  defaultOpen?: boolean;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  evidence,
  defaultOpen = false,
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (!evidence) {
    return (
      <div className="rounded-lg border border-border-subtle bg-bg-surface p-4 text-xs font-mono text-txt-dim">
        No detailed acoustic evidence generated for this evaluation.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border-strong bg-bg-surface overflow-hidden shadow-panel">
      {/* Header Button Toggle for Progressive Disclosure */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-4 flex items-center justify-between bg-bg-surface hover:bg-bg-surface-hover transition-colors text-left select-none"
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded bg-brand/10 text-brand border border-brand/20">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-mono font-bold text-txt-main">Why this result? (Acoustic Evidence)</h4>
            <p className="text-[11px] font-mono text-txt-muted">
              Inspect underlying acoustic feature contributions, operating points & signal provenance
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-brand">
          <span>{isOpen ? 'Collapse Details' : 'Expand Details'}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expandable Technical Evidence Body */}
      {isOpen && (
        <div className="p-5 border-t border-border-subtle bg-bg-surface/50 space-y-6 animate-in slide-in-from-top-2 duration-200">
          
          {/* Signal Contribution Breakdown */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono font-semibold text-txt-main">
              <Layers className="w-4 h-4 text-brand" />
              <span>Acoustic Signal Contribution Breakdown</span>
            </div>
            
            <div className="space-y-2">
              {evidence.signal_contributions.map((sig, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded bg-bg-surface-elevated border border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono"
                >
                  <div className="space-y-0.5 max-w-lg">
                    <span className="font-semibold text-txt-main">{sig.feature}</span>
                    <p className="text-[11px] text-txt-muted">{sig.description}</p>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span
                      className={cn(
                        'text-[11px] px-2 py-0.5 rounded font-semibold',
                        sig.direction === 'synthetic_bias'
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : sig.direction === 'human_bias'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-bg-surface text-txt-dim border border-border-subtle'
                      )}
                    >
                      {sig.direction === 'synthetic_bias'
                        ? 'Synthetic Artifact'
                        : sig.direction === 'human_bias'
                        ? 'Human Acoustic'
                        : 'Neutral'}
                    </span>
                    <span className="font-bold text-txt-main w-12 text-right">
                      {(sig.weight * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Audio Condition & Provenance Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-3.5 rounded bg-bg-surface-elevated border border-border-subtle space-y-1">
              <div className="flex items-center gap-1.5 text-txt-dim text-[11px] uppercase font-semibold">
                <Info className="w-3.5 h-3.5 text-brand" />
                <span>Audio Condition & Degradation</span>
              </div>
              <p className="text-txt-main font-medium">{evidence.audio_condition}</p>
            </div>

            <div className="p-3.5 rounded bg-bg-surface-elevated border border-border-subtle space-y-1">
              <div className="flex items-center gap-1.5 text-txt-dim text-[11px] uppercase font-semibold">
                <FileCheck className="w-3.5 h-3.5 text-brand" />
                <span>Acoustic Provenance & Engine</span>
              </div>
              <p className="text-txt-main font-medium">{evidence.provenance}</p>
            </div>
          </div>

          {/* Model Operating Points & Logit Parameters */}
          <div className="p-3.5 rounded bg-bg-surface-elevated border border-border-subtle space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between text-txt-dim text-[11px] font-semibold border-b border-border-subtle pb-1">
              <span>Threshold Calibration Protocol (Phase 6)</span>
              <span>Model: {evidence.model_name} ({evidence.model_version})</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-txt-muted text-[11px]">
              <div>Low Threshold (θ_low): <span className="font-bold text-txt-main">{evidence.low_threshold}</span></div>
              <div>High Threshold (θ_high): <span className="font-bold text-txt-main">{evidence.high_threshold}</span></div>
              <div>Raw Score (Logit): <span className="font-bold text-txt-main">{evidence.raw_score ?? 'N/A'}</span></div>
              <div>Calibration ECE: <span className="font-bold text-txt-main">{evidence.ece_score ?? 'N/A'}</span></div>
            </div>
          </div>

        </div>
      )}
    </div>
  );
};
