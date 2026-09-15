import React from 'react';
import { RecordingProvenance } from '../../types/investigation';
import { ShieldCheck, Info, FileCheck2 } from 'lucide-react';
import { cn } from '../../lib/utils';

interface RecordingInfoProps {
  provenance: RecordingProvenance;
  className?: string;
}

export const RecordingInfo: React.FC<RecordingInfoProps> = ({
  provenance,
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
        <div className="flex items-center gap-2">
          <FileCheck2 className="w-4 h-4 text-brand" />
          <h3 className="text-sm font-semibold text-txt-main tracking-tight">
            Recording Information
          </h3>
        </div>
        <span className="text-[11px] font-mono text-txt-dim">
          Provenance & Integrity
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Digital Credentials */}
        <div className="p-3.5 rounded-lg bg-bg-surface-elevated border border-border-subtle flex items-center justify-between">
          <div>
            <span className="text-xs text-txt-muted block">Digital credentials</span>
            <span className="text-sm font-semibold text-txt-main font-mono">
              {provenance.digitalCredentials}
            </span>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-bg-surface text-txt-dim border border-border-subtle">
            C2PA / Provenance
          </span>
        </div>

        {/* Audio Watermark */}
        <div className="p-3.5 rounded-lg bg-bg-surface-elevated border border-border-subtle flex items-center justify-between">
          <div>
            <span className="text-xs text-txt-muted block">Audio watermark</span>
            <span className="text-sm font-semibold text-txt-main font-mono">
              {provenance.audioWatermark}
            </span>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-bg-surface text-txt-dim border border-border-subtle">
            Acoustic Marker
          </span>
        </div>
      </div>

      {/* Mandatory PRD advisory: Absence of credentials does not imply guilt */}
      <div className="p-3 rounded-md bg-blue-500/10 border border-blue-500/20 flex items-start gap-2.5 text-xs text-blue-400">
        <Info className="w-4 h-4 shrink-0 mt-0.5 text-blue-400" />
        <p className="leading-relaxed">
          <span className="font-semibold text-blue-300">Regulatory & Evidence Notice: </span>
          {provenance.advisoryNote ||
            'The absence of these credentials does not by itself indicate synthetic audio.'}
        </p>
      </div>
    </div>
  );
};
