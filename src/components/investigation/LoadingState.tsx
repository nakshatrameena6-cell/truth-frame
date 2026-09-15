import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

interface LoadingStateProps {
  message?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading investigation...',
  className,
}) => {
  return (
    <div
      className={cn(
        'max-w-md mx-auto py-16 text-center space-y-3 font-mono text-xs text-txt-muted',
        className
      )}
      role="status"
    >
      <Loader2 className="w-8 h-8 text-brand animate-spin mx-auto" />
      <p>{message}</p>
    </div>
  );
};
