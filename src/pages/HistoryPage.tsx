import React, { useState, useMemo } from 'react';
import { Search, Plus, SlidersHorizontal, ArrowUpDown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AnalysisTable } from '../components/investigation/AnalysisTable';
import { EmptyState } from '../components/investigation/EmptyState';
import { MOCK_HISTORY_REPORTS } from '../lib/mockScenarios';
import { InvestigationResult } from '../types/investigation';
import { cn } from '../lib/utils';

type FilterTab = 'all' | InvestigationResult;

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<FilterTab>('all');

  // Filter and search logic
  const filteredReports = useMemo(() => {
    return MOCK_HISTORY_REPORTS.filter((report) => {
      // 1. Tab filter
      if (activeTab !== 'all' && report.result !== activeTab) {
        return false;
      }

      // 2. Search query (case reference or recording name)
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesCase = (report.caseReference || '').toLowerCase().includes(q);
        const matchesName = report.recordingName.toLowerCase().includes(q);
        const matchesId = report.id.toLowerCase().includes(q);
        return matchesCase || matchesName || matchesId;
      }

      return true;
    });
  }, [searchQuery, activeTab]);

  // Tab counts
  const tabCounts = useMemo(() => {
    return {
      all: MOCK_HISTORY_REPORTS.length,
      likely_synthetic: MOCK_HISTORY_REPORTS.filter((r) => r.result === 'likely_synthetic').length,
      consistent_with_human: MOCK_HISTORY_REPORTS.filter((r) => r.result === 'consistent_with_human').length,
      inconclusive: MOCK_HISTORY_REPORTS.filter((r) => r.result === 'inconclusive').length,
    };
  }, []);

  const tabs: { id: FilterTab; label: string; count: number }[] = [
    { id: 'all', label: 'All', count: tabCounts.all },
    { id: 'likely_synthetic', label: 'Likely Synthetic', count: tabCounts.likely_synthetic },
    { id: 'consistent_with_human', label: 'Consistent with Human', count: tabCounts.consistent_with_human },
    { id: 'inconclusive', label: 'Inconclusive', count: tabCounts.inconclusive },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-subtle pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-txt-main">
            Analysis History
          </h1>
          <p className="text-xs text-txt-muted mt-1">
            Complete audit trail of past call recording evaluations and determinations
          </p>
        </div>

        <button
          onClick={() => navigate('/analyze')}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand hover:bg-brand-hover text-white text-xs font-semibold shadow-subtle transition-all active:scale-[0.99] self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>+ New Analysis</span>
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-txt-dim absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search cases or recordings..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-lg bg-bg-surface border border-border-subtle text-xs text-txt-main placeholder:text-txt-dim focus:outline-none focus:ring-1 focus:ring-brand font-mono"
            />
          </div>

          <div className="text-xs font-mono text-txt-dim">
            Showing {filteredReports.length} of {MOCK_HISTORY_REPORTS.length} cases
          </div>
        </div>

        {/* Filter Tabs: [All] [Likely Synthetic] [Consistent with Human] [Inconclusive] */}
        <div className="flex items-center gap-1.5 border-b border-border-subtle overflow-x-auto pb-1">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-2 px-3.5 py-2 text-xs font-mono rounded-t-md transition-all whitespace-nowrap border-b-2',
                  isActive
                    ? 'border-brand text-brand font-bold bg-brand/5'
                    : 'border-transparent text-txt-muted hover:text-txt-main hover:bg-bg-surface-hover'
                )}
              >
                <span>{tab.label}</span>
                <span
                  className={cn(
                    'text-[10px] px-1.5 py-0.2 rounded font-bold',
                    isActive ? 'bg-brand/20 text-brand' : 'bg-bg-surface-elevated text-txt-dim'
                  )}
                >
                  {tab.count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Table or Empty State */}
      {filteredReports.length === 0 ? (
        <EmptyState
          title="No Matching Cases Found"
          description={`No recorded investigations match "${searchQuery}" under the selected filter.`}
          actionLabel="Clear Search Filter"
          actionHref="#"
          className="my-8"
        />
      ) : (
        <AnalysisTable reports={filteredReports} />
      )}
    </div>
  );
};
