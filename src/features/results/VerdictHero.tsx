import React from 'react';
import { Verdict } from '../../types/api';
import { VerdictBadge } from '../../components/VerdictBadge';
import { ShieldCheck, AlertTriangle, AlertCircle, HelpCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

interface VerdictHeroProps {
  verdict: Verdict | null | undefined;
  filename: string;
  durationSeconds: number;
  format: string;
  language: string | null;
}

export const VerdictHero: React.FC<VerdictHeroProps> = ({
  verdict,
  filename,
  durationSeconds,
  format,
  language,
}) => {
  const getVerdictExplanation = (v: Verdict | null | undefined) => {
    switch (v) {
      case 'consistent_with_human':
        return 'Acoustic spectral features, energy dynamics, and phase alignment align with natural human vocal apparatus.';
      case 'inconclusive':
        return 'The available acoustic evidence was not strong enough to classify this recording reliably. Signal degradation or codec compression prevents definitive score thresholding.';
      case 'likely_synthetic':
        return 'Acoustic feature extraction detected synthetic vocoder phase patterns and spectral flux anomalies consistent with neural speech synthesis.';
      default:
        return 'Analysis pending or unclassified.';
    }
  };

  return (
    <div className="rounded-lg border border-border-strong bg-bg-surface p-6 space-y-4 shadow-panel">
      {/* File & Audio Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-txt-muted pb-3 border-b border-border-subtle">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-txt-main">{filename}</span>
        </div>
        <div className="flex items-center gap-2">
          <span>{durationSeconds ? `${durationSeconds.toFixed(1)}s` : '--'}</span>
          <span>·</span>
          <span className="uppercase">{format}</span>
          <span>·</span>
          <span>{language ? language.toUpperCase() : 'UNKNOWN'}</span>
        </div>
      </div>

      {/* Hero Verdict Classification Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-1">
        <div className="space-y-2">
          <div className="text-[11px] font-mono uppercase tracking-wider text-txt-dim">
            Backend Calibration Verdict
          </div>
          <VerdictBadge verdict={verdict} size="lg" />
        </div>

        {/* Disclaimer Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-bg-surface-elevated border border-border-subtle text-[11px] font-mono text-txt-muted">
          <HelpCircle className="w-3.5 h-3.5 text-brand shrink-0" />
          <span>Experimental Detector · Statistical Probability</span>
        </div>
      </div>

      {/* Concise Analyst Guidance Description */}
      <p className="text-xs text-txt-muted leading-relaxed font-sans pt-1">
        {getVerdictExplanation(verdict)}
      </p>
    </div>
  );
};
