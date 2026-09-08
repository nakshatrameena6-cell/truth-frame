import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listAnalyses, deleteAnalysis } from '../api/analyses';
import { AnalysisRecord, Verdict } from '../types/api';
import { AnalysisFilters } from '../features/history/AnalysisFilters';
import { AnalysisTable } from '../features/history/AnalysisTable';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { History, FileAudio } from 'lucide-react';

export const HistoryPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [verdictFilter, setVerdictFilter] = useState<Verdict | 'all' | 'failed'>('all');
  const [deletingRecord, setDeletingRecord] = useState<AnalysisRecord | null>(null);

  const { data: records = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['analyses'],
    queryFn: listAnalyses,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAnalysis(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analyses'] });
      setDeletingRecord(null);
    },
  });

  const filteredRecords = useMemo(() => {
    return records.filter((rec) => {
      // Search filter
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        rec.audio.filename.toLowerCase().includes(q) ||
        rec.analysis_id.toLowerCase().includes(q) ||
        (rec.audio.language && rec.audio.language.toLowerCase().includes(q));

      // Verdict/Status filter
      let matchesVerdict = true;
      if (verdictFilter === 'failed') {
        matchesVerdict = rec.status === 'failed';
      } else if (verdictFilter !== 'all') {
        matchesVerdict = rec.verdict === verdictFilter;
      }

      return matchesSearch && matchesVerdict;
    });
  }, [records, searchQuery, verdictFilter]);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-brand" />
            <h1 className="text-xl font-bold font-mono tracking-tight text-txt-main">
              Evaluation History Archive
            </h1>
          </div>
          <p className="text-xs text-txt-muted font-sans">
            Search, filter, and inspect previously executed audio authenticity evaluations.
          </p>
        </div>

        <div className="text-xs font-mono text-txt-dim px-3 py-1.5 rounded bg-bg-surface-elevated border border-border-subtle">
          Total Archive Records: <span className="font-bold text-txt-main">{records.length}</span>
        </div>
      </div>

      {/* Filter Bar */}
      <AnalysisFilters
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        verdictFilter={verdictFilter}
        onVerdictFilterChange={setVerdictFilter}
        onRefresh={() => refetch()}
        totalCount={records.length}
      />

      {/* High Density Table */}
      {isLoading ? (
        <div className="rounded-lg border border-border-strong bg-bg-surface p-12 text-center space-y-3 shadow-panel">
          <div className="w-8 h-8 rounded-full border-2 border-brand border-t-transparent animate-spin mx-auto" />
          <p className="text-xs font-mono text-txt-muted">Loading evaluation records...</p>
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-6 text-xs font-mono text-rose-400">
          Failed to load evaluation history. Please refresh the page.
        </div>
      ) : (
        <AnalysisTable
          records={filteredRecords}
          onDeleteRequest={(rec) => setDeletingRecord(rec)}
        />
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmDialog
        isOpen={!!deletingRecord}
        title="Delete Audio Evaluation Record"
        description={`Are you sure you want to delete the evaluation report for "${deletingRecord?.audio.filename}" (${deletingRecord?.analysis_id})? This action cannot be undone.`}
        confirmLabel="Delete Record"
        isDestructive={true}
        onConfirm={() => {
          if (deletingRecord) {
            deleteMutation.mutate(deletingRecord.analysis_id);
          }
        }}
        onCancel={() => setDeletingRecord(null)}
      />
    </div>
  );
};
