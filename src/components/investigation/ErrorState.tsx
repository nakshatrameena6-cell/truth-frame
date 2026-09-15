import React from 'react';
import { AlertCircle, RotateCcw, ArrowLeft } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useNavigate } from 'react-router-dom';

interface ErrorStateProps {
  title?: string;
  whatHappened?: string;
  why?: string;
  whatToDoNext?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "We couldn't complete the analysis",
  whatHappened = 'The recording could not be processed.',
  why = 'The audio stream was truncated or could not be decoded reliably.',
  whatToDoNext = 'Try uploading the recording again or verify the file is not damaged.',
  onRetry,
  className,
}) => {
  const navigate = useNavigate();

  return (
    <div
      className={cn(
        'max-w-md mx-auto p-6 rounded-lg border border-rose-500/25 bg-bg-surface space-y-5 shadow-panel text-left',
        className
      )}
      role="alert"
    >
      <div className="flex items-center gap-3 border-b border-border-subtle pb-3">
        <div className="w-9 h-9 rounded-full bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-500 shrink-0">
          <AlertCircle className="w-5 h-5" />
        </div>
        <h3 className="text-sm font-bold text-txt-main">
          {title}
        </h3>
      </div>

      <div className="space-y-3 text-xs">
        <div>
          <span className="font-semibold text-txt-dim uppercase tracking-wider block font-mono text-[10px]">
            What happened?
          </span>
          <p className="text-txt-main mt-0.5 font-medium">{whatHappened}</p>
        </div>

        <div>
          <span className="font-semibold text-txt-dim uppercase tracking-wider block font-mono text-[10px]">
            Why?
          </span>
          <p className="text-txt-muted mt-0.5 leading-relaxed">{why}</p>
        </div>

        <div>
          <span className="font-semibold text-txt-dim uppercase tracking-wider block font-mono text-[10px]">
            What should I do next?
          </span>
          <p className="text-txt-muted mt-0.5 leading-relaxed">{whatToDoNext}</p>
        </div>
      </div>

      <div className="flex items-center gap-3 pt-2 border-t border-border-subtle">
        {onRetry && (
          <button
            onClick={onRetry}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-brand hover:bg-brand-hover text-white text-xs font-medium transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Try Again</span>
          </button>
        )}
        <button
          onClick={() => navigate('/analyze')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-bg-surface-elevated border border-border-subtle hover:bg-bg-surface-hover text-txt-muted hover:text-txt-main text-xs font-mono transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>New Analysis</span>
        </button>
      </div>
    </div>
  );
};
