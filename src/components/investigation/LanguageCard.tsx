import React from 'react';
import { LanguageDetection } from '../../types/investigation';
import { Languages, AlertCircle, CheckCircle2 } from 'lucide-react';
import { cn } from '../../lib/utils';

interface LanguageCardProps {
  language: LanguageDetection;
  className?: string;
}

export const LanguageCard: React.FC<LanguageCardProps> = ({
  language,
  className,
}) => {
  return (
    <div
      className={cn(
        'rounded-lg border border-border-subtle bg-bg-surface p-5 space-y-3 shadow-sm',
        className
      )}
    >
      <div className="flex items-center justify-between border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2">
          <Languages className="w-4 h-4 text-brand" />
          <h3 className="text-sm font-semibold text-txt-main tracking-tight">
            Language
          </h3>
        </div>
        <span className="text-[11px] font-mono text-txt-dim">
          Linguistic Alignment
        </span>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span className="text-xs text-txt-muted block">Language detected</span>
            <span className="text-base font-bold text-txt-main font-mono">
              {language.detected}
            </span>
          </div>

          {language.isCodeSwitching && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-blue-500/10 border border-blue-500/20 text-xs font-mono text-blue-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{language.codeSwitchingDetails || 'Code-switching detected'}</span>
            </span>
          )}
        </div>

        {/* Unsupported Language Caution Notice */}
        {!language.isSupported && (
          <div className="mt-2 p-3 rounded-md bg-amber-500/10 border border-amber-500/20 flex items-start gap-2.5 text-xs text-amber-400 font-mono">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-500" />
            <div>
              <p className="font-semibold text-amber-300">
                Language support is limited for this recording.
              </p>
              <p className="text-amber-400/90 text-[11px] mt-0.5">
                {language.guidanceNote || 'Interpret the result with caution.'}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
