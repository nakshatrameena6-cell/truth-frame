import React from 'react';
import { CheckCircle2, CircleDot, Circle, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

export type ProgressStep =
  | 'received'
  | 'quality_reviewed'
  | 'analysing_speech'
  | 'preparing_result';

interface AnalysisProgressProps {
  filename: string;
  currentStep: ProgressStep;
  onCancel?: () => void;
  className?: string;
}

export const AnalysisProgress: React.FC<AnalysisProgressProps> = ({
  filename,
  currentStep,
  onCancel,
  className,
}) => {
  const steps: { key: ProgressStep; label: string }[] = [
    { key: 'received', label: 'Recording received' },
    { key: 'quality_reviewed', label: 'Recording quality reviewed' },
    { key: 'analysing_speech', label: 'Analysing speech' },
    { key: 'preparing_result', label: 'Preparing result' },
  ];

  const stepKeys = steps.map((s) => s.key);
  const currentIndex = stepKeys.indexOf(currentStep);

  return (
    <div
      className={cn(
        'max-w-md mx-auto p-6 rounded-lg border border-border-subtle bg-bg-surface space-y-6 shadow-panel',
        className
      )}
      role="status"
      aria-live="polite"
    >
      <div className="text-center space-y-1">
        <h3 className="text-lg font-bold tracking-tight text-txt-main">
          Analysing recording
        </h3>
        <p className="text-xs font-mono text-txt-muted truncate max-w-xs mx-auto">
          {filename}
        </p>
      </div>

      {/* Progress Steps List */}
      <div className="space-y-3.5 py-2">
        {steps.map((step, idx) => {
          const isDone = idx < currentIndex;
          const isCurrent = idx === currentIndex;
          const isPending = idx > currentIndex;

          return (
            <div
              key={step.key}
              className={cn(
                'flex items-center gap-3 text-sm font-medium transition-colors',
                isDone
                  ? 'text-emerald-500'
                  : isCurrent
                  ? 'text-brand font-semibold'
                  : 'text-txt-dim'
              )}
            >
              <div className="shrink-0 w-5 h-5 flex items-center justify-center">
                {isDone && <CheckCircle2 className="w-5 h-5 text-emerald-500" />}
                {isCurrent && (
                  <Loader2 className="w-5 h-5 text-brand animate-spin" />
                )}
                {isPending && <Circle className="w-4 h-4 text-txt-dim/40" />}
              </div>

              <span>{step.label}</span>
            </div>
          );
        })}
      </div>

      {onCancel && (
        <div className="pt-2 text-center border-t border-border-subtle">
          <button
            onClick={onCancel}
            className="text-xs font-mono text-txt-dim hover:text-txt-main transition-colors"
          >
            Cancel Analysis
          </button>
        </div>
      )}
    </div>
  );
};
