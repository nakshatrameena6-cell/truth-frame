import React from 'react';
import { Loader2, CheckCircle2, AlertCircle, XCircle, RefreshCw } from 'lucide-react';
import { AnalysisStatus } from '../../types/api';
import { cn } from '../../lib/utils';

interface UploadProgressProps {
  status: AnalysisStatus | 'uploading' | 'idle';
  filename: string;
  onCancel?: () => void;
  onRetry?: () => void;
  errorMessage?: string | null;
}

export const UploadProgress: React.FC<UploadProgressProps> = ({
  status,
  filename,
  onCancel,
  onRetry,
  errorMessage,
}) => {
  if (status === 'idle') return null;

  const stages = [
    { key: 'uploading', label: 'Uploading audio stream' },
    { key: 'queued', label: 'Queued for evaluation' },
    { key: 'processing', label: 'Running acoustic feature extraction & inference' },
    { key: 'completed', label: 'Calibrating operating point & generating report' },
  ];

  const getCurrentStepIndex = () => {
    switch (status) {
      case 'uploading':
        return 0;
      case 'queued':
        return 1;
      case 'processing':
        return 2;
      case 'completed':
        return 3;
      case 'failed':
        return 2;
      default:
        return 0;
    }
  };

  const currentStep = getCurrentStepIndex();

  return (
    <div className="rounded-lg border border-border-strong bg-bg-surface p-6 space-y-5 animate-in fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded bg-brand/10 border border-brand/20 flex items-center justify-center text-brand">
            {status === 'failed' ? (
              <AlertCircle className="w-5 h-5 text-rose-500" />
            ) : (
              <Loader2 className="w-5 h-5 animate-spin text-brand" />
            )}
          </div>
          <div>
            <h4 className="text-xs font-semibold text-txt-main font-mono">{filename}</h4>
            <p className="text-[11px] text-txt-muted font-mono">
              {status === 'failed' ? 'Analysis Failed' : 'Processing audio payload...'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {status !== 'completed' && status !== 'failed' && onCancel && (
            <button
              onClick={onCancel}
              className="px-2.5 py-1 rounded bg-bg-surface-elevated border border-border-subtle text-txt-muted hover:text-txt-main text-xs font-mono transition-colors flex items-center gap-1"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>Cancel</span>
            </button>
          )}

          {status === 'failed' && onRetry && (
            <button
              onClick={onRetry}
              className="px-3 py-1 rounded bg-brand hover:bg-brand-hover text-white text-xs font-mono font-semibold transition-colors flex items-center gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Analysis</span>
            </button>
          )}
        </div>
      </div>

      {/* Staged Stepper Progress */}
      {status !== 'failed' ? (
        <div className="space-y-2.5 pt-2">
          {stages.map((stage, idx) => {
            const isDone = idx < currentStep;
            const isCurrent = idx === currentStep;

            return (
              <div key={stage.key} className="flex items-center gap-3">
                <div className="flex items-center justify-center w-5 h-5 rounded-full text-[11px] font-mono font-bold">
                  {isDone ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 animate-spin text-brand" />
                  ) : (
                    <span className="w-2 h-2 rounded-full bg-border-strong" />
                  )}
                </div>
                <span
                  className={cn(
                    'text-xs font-mono',
                    isDone
                      ? 'text-txt-muted line-through opacity-70'
                      : isCurrent
                      ? 'text-txt-main font-semibold'
                      : 'text-txt-dim'
                  )}
                >
                  {stage.label}
                </span>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="p-3.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-mono space-y-1">
          <div className="font-semibold text-rose-500 flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4" />
            <span>Detection Process Terminated</span>
          </div>
          <p className="text-txt-muted">{errorMessage || 'An error occurred during audio feature extraction.'}</p>
        </div>
      )}
    </div>
  );
};
