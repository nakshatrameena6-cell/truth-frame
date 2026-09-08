import React from 'react';
import { ModelInfo } from '../../types/api';

interface ModelMetadataProps {
  model?: { name: string; version: string } | ModelInfo;
}

export const ModelMetadata: React.FC<ModelMetadataProps> = ({ model }) => {
  const name = model?.name || 'PandaMIND Detector';
  const version = model?.version || 'phase9-experimental';

  return (
    <div className="rounded-lg border border-border-strong bg-bg-surface p-5 space-y-3 shadow-panel">
      <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-txt-dim pb-2 border-b border-border-subtle">
        Inference & Model Parameters
      </h4>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        <div className="p-2.5 rounded bg-bg-surface-elevated border border-border-subtle space-y-0.5">
          <span className="text-[10px] text-txt-dim block uppercase">Model Name</span>
          <span className="font-medium text-txt-main truncate block">{name}</span>
        </div>
        <div className="p-2.5 rounded bg-bg-surface-elevated border border-border-subtle space-y-0.5">
          <span className="text-[10px] text-txt-dim block uppercase">Version</span>
          <span className="font-medium text-amber-500 truncate block">{version}</span>
        </div>
        <div className="p-2.5 rounded bg-bg-surface-elevated border border-border-subtle space-y-0.5">
          <span className="text-[10px] text-txt-dim block uppercase">Low Operating Point</span>
          <span className="font-medium text-txt-main truncate block">0.7408 (θ_low)</span>
        </div>
        <div className="p-2.5 rounded bg-bg-surface-elevated border border-border-subtle space-y-0.5">
          <span className="text-[10px] text-txt-dim block uppercase">High Operating Point</span>
          <span className="font-medium text-txt-main truncate block">0.7556 (θ_high)</span>
        </div>
      </div>
    </div>
  );
};
