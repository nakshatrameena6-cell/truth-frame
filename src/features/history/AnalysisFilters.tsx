import React from 'react';
import { Search, Filter, RefreshCw } from 'lucide-react';
import { Verdict } from '../../types/api';
import { cn } from '../../lib/utils';

interface AnalysisFiltersProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  verdictFilter: Verdict | 'all' | 'failed';
  onVerdictFilterChange: (v: Verdict | 'all' | 'failed') => void;
  onRefresh?: () => void;
  totalCount: number;
}

export const AnalysisFilters: React.FC<AnalysisFiltersProps> = ({
  searchQuery,
  onSearchChange,
  verdictFilter,
  onVerdictFilterChange,
  onRefresh,
  totalCount,
}) => {
  const tabs: Array<{ key: Verdict | 'all' | 'failed'; label: string }> = [
    { key: 'all', label: 'All Evaluations' },
    { key: 'consistent_with_human', label: 'Consistent with Human' },
    { key: 'inconclusive', label: 'Inconclusive' },
    { key: 'likely_synthetic', label: 'Likely Synthetic' },
    { key: 'failed', label: 'Failed' },
  ];

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-4 rounded-lg border border-border-strong bg-bg-surface shadow-panel">
      {/* Search Input */}
      <div className="relative max-w-sm w-full">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-txt-dim" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by filename, language, ID..."
          className="w-full pl-9 pr-4 py-1.5 rounded bg-bg-surface-elevated border border-border-subtle text-xs font-mono text-txt-main placeholder:text-txt-dim focus:outline-none focus:border-brand"
        />
      </div>

      {/* Filter Tabs & Refresh Button */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
        <div className="flex items-center gap-1 bg-bg-surface-elevated p-1 rounded border border-border-subtle">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => onVerdictFilterChange(tab.key)}
              className={cn(
                'px-2.5 py-1 rounded text-xs font-mono transition-colors whitespace-nowrap',
                verdictFilter === tab.key
                  ? 'bg-bg-surface text-brand font-semibold shadow-subtle border border-border-subtle'
                  : 'text-txt-muted hover:text-txt-main'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            className="p-2 rounded bg-bg-surface-elevated border border-border-subtle text-txt-muted hover:text-txt-main transition-colors shrink-0"
            title="Refresh history list"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};
