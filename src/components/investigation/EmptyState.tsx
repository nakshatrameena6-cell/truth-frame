import React from 'react';
import { FileQuestion, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '../../lib/utils';

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionLabel?: string;
  actionHref?: string;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Investigations Found',
  description = 'No call recordings have been analysed yet for this filter.',
  actionLabel = 'New Analysis',
  actionHref = '/analyze',
  className,
}) => {
  return (
    <div
      className={cn(
        'max-w-md mx-auto py-12 px-6 text-center space-y-4 rounded-lg border border-dashed border-border-strong bg-bg-surface',
        className
      )}
    >
      <div className="w-12 h-12 rounded-full bg-bg-surface-elevated text-txt-dim flex items-center justify-center mx-auto border border-border-subtle">
        <FileQuestion className="w-6 h-6" />
      </div>

      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-txt-main">{title}</h3>
        <p className="text-xs text-txt-muted">{description}</p>
      </div>

      {actionHref && (
        <div className="pt-2">
          <Link
            to={actionHref}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-brand hover:bg-brand-hover text-white text-xs font-semibold shadow-subtle transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>{actionLabel}</span>
          </Link>
        </div>
      )}
    </div>
  );
};
