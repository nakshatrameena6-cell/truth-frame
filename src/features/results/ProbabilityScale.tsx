import React from 'react';
import { Verdict } from '../../types/api';
import { cn } from '../../lib/utils';

interface ProbabilityScaleProps {
  probability: number | null; // 0.0 to 1.0
  confidence?: number | null; // 0.0 to 1.0
  verdict: Verdict | null;
  lowThreshold?: number; // e.g. 0.7408
  highThreshold?: number; // e.g. 0.7556
}

export const ProbabilityScale: React.FC<ProbabilityScaleProps> = ({
  probability,
  confidence,
  verdict,
  lowThreshold = 0.7408,
  highThreshold = 0.7556,
}) => {
  if (probability === null || probability === undefined) return null;

  const pct = Math.min(100, Math.max(0, probability * 100));
  const lowPct = Math.min(100, Math.max(0, lowThreshold * 100));
  const highPct = Math.min(100, Math.max(0, highThreshold * 100));

  const getTrackColor = (v: Verdict | null) => {
    switch (v) {
      case 'consistent_with_human':
        return 'bg-emerald-500';
      case 'inconclusive':
        return 'bg-amber-500';
      case 'likely_synthetic':
        return 'bg-rose-500';
      default:
        return 'bg-brand';
    }
  };

  return (
    <div className="rounded-lg border border-border-strong bg-bg-surface p-5 space-y-4 shadow-panel">
      {/* Top Header Metrics Row */}
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <div className="text-[11px] font-mono uppercase tracking-wider text-txt-dim">
            Synthetic Probability
          </div>
          <div className="flex items-baseline gap-2 mt-0.5">
            <span className="text-2xl font-mono font-bold text-txt-main">
              {pct.toFixed(1)}%
            </span>
            <span className="text-xs font-mono text-txt-muted">
              ({probability.toFixed(3)})
            </span>
          </div>
        </div>

        {confidence !== null && confidence !== undefined && (
          <div className="text-right">
            <div className="text-[11px] font-mono uppercase tracking-wider text-txt-dim">
              Calibrated Confidence
            </div>
            <div className="text-lg font-mono font-bold text-txt-main mt-0.5">
              {(confidence * 100).toFixed(0)}%
            </div>
          </div>
        )}
      </div>

      {/* Horizontal Restrained Technical Scale Axis */}
      <div className="space-y-2 pt-1">
        <div className="relative h-3 w-full rounded bg-bg-surface-elevated border border-border-subtle overflow-hidden">
          
          {/* Background Band Visualizer for Inconclusive Region */}
          <div
            className="absolute top-0 bottom-0 bg-amber-500/15 border-x border-amber-500/30"
            style={{
              left: `${lowPct}%`,
              width: `${highPct - lowPct}%`,
            }}
            title={`Inconclusive Band (${lowThreshold} to ${highThreshold})`}
          />

          {/* Probability Indicator Bar */}
          <div
            className={cn('h-full transition-all duration-500 rounded-sm', getTrackColor(verdict))}
            style={{ width: `${pct}%` }}
          />

          {/* Low Threshold Marker Line */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-amber-500 z-10"
            style={{ left: `${lowPct}%` }}
          />

          {/* High Threshold Marker Line */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-rose-500 z-10"
            style={{ left: `${highPct}%` }}
          />
        </div>

        {/* Axis Labels */}
        <div className="flex justify-between text-[10px] font-mono text-txt-dim">
          <span>0% (Human)</span>
          <span style={{ marginLeft: `${lowPct - 10}%` }}>
            Low ({lowThreshold.toFixed(2)})
          </span>
          <span>High ({highThreshold.toFixed(2)})</span>
          <span>100% (Synthetic)</span>
        </div>
      </div>
    </div>
  );
};
