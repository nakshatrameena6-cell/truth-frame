import React from 'react';
import { Cpu } from 'lucide-react';
import { cn } from '../lib/utils';

interface ModelStatusBadgeProps {
  name?: string;
  version?: string;
  className?: string;
}

export const ModelStatusBadge: React.FC<ModelStatusBadgeProps> = ({
  name = 'PandaMIND Detector',
  version = 'phase9-experimental',
  className,
}) => {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 px-2.5 py-1 rounded bg-bg-surface-elevated border border-border-subtle text-xs text-txt-muted font-mono select-none',
        className
      )}
      title="Detector Engine Status"
    >
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75"></span>
        <span className="relative inline-flex rounded-full h-2 w-2 bg-brand"></span>
      </span>
      <Cpu className="w-3.5 h-3.5 text-txt-dim" />
      <span className="font-medium text-txt-main">{name}</span>
      <span className="text-border-strong">|</span>
      <span className="text-[11px] text-amber-500 font-semibold px-1 py-0.2 rounded bg-amber-500/10 border border-amber-500/20">
        Experimental
      </span>
      <span className="text-txt-dim hidden sm:inline">{version}</span>
    </div>
  );
};
