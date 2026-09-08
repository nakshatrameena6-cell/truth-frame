import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { cn } from '../lib/utils';

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDestructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isDestructive = false,
  onConfirm,
  onCancel,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-bg-surface border border-border-strong rounded-lg shadow-panel max-w-md w-full p-5 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            {isDestructive && (
              <div className="p-2 rounded bg-rose-500/10 text-rose-500 border border-rose-500/20">
                <AlertTriangle className="w-5 h-5" />
              </div>
            )}
            <h3 className="font-semibold text-sm text-txt-main">{title}</h3>
          </div>
          <button
            onClick={onCancel}
            className="text-txt-dim hover:text-txt-main p-1 rounded hover:bg-bg-surface-hover transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-txt-muted leading-relaxed">{description}</p>

        <div className="flex items-center justify-end gap-2 pt-2 border-t border-border-subtle">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 rounded text-xs font-medium text-txt-muted hover:text-txt-main hover:bg-bg-surface-hover border border-border-subtle transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={cn(
              'px-3 py-1.5 rounded text-xs font-semibold text-white transition-colors',
              isDestructive
                ? 'bg-rose-600 hover:bg-rose-700'
                : 'bg-brand hover:bg-brand-hover'
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
