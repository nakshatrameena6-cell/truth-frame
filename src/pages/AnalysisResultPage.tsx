import React from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAnalysis } from '../api/analyses';
import { VerdictHero } from '../features/results/VerdictHero';
import { ProbabilityScale } from '../features/results/ProbabilityScale';
import { AudioPlayer } from '../features/results/AudioPlayer';
import { AudioMetadata } from '../features/results/AudioMetadata';
import { ModelMetadata } from '../features/results/ModelMetadata';
import { EvidenceDrawer } from '../features/results/EvidenceDrawer';
import { UploadProgress } from '../features/upload/UploadProgress';
import { getHumanReadableErrorMessage } from '../lib/errors';
import { ArrowLeft, RefreshCw, FileText, AlertCircle } from 'lucide-react';

export const AnalysisResultPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: record, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['analysis', id],
    queryFn: () => getAnalysis(id || ''),
    enabled: !!id,
    // Poll approximately every 1 second while queued or processing. Stop on completed/failed.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'queued' || status === 'processing') {
        return 1000;
      }
      return false;
    },
  });

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-12 space-y-4 text-center font-mono">
        <div className="w-10 h-10 rounded-full border-2 border-brand border-t-transparent animate-spin mx-auto" />
        <p className="text-xs text-txt-muted">Fetching analysis report payload...</p>
      </div>
    );
  }

  if (isError || !record) {
    const errorObj = error as any;
    const msg = getHumanReadableErrorMessage(errorObj?.error_code, errorObj?.message);

    return (
      <div className="max-w-3xl mx-auto py-12 space-y-6">
        <button
          onClick={() => navigate('/history')}
          className="flex items-center gap-2 text-xs font-mono text-txt-muted hover:text-txt-main transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Analysis History</span>
        </button>

        <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-6 space-y-3 font-mono text-xs text-rose-400">
          <div className="flex items-center gap-2 font-semibold text-rose-500 text-sm">
            <AlertCircle className="w-5 h-5" />
            <span>Analysis Report Unavailable</span>
          </div>
          <p>{msg}</p>
          <div className="pt-2">
            <button
              onClick={() => refetch()}
              className="px-3 py-1.5 rounded bg-bg-surface border border-border-strong text-txt-main hover:bg-bg-surface-hover transition-colors"
            >
              Retry Request
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Active queuing or processing state
  if (record.status === 'queued' || record.status === 'processing') {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <button
            onClick={() => navigate('/analyze')}
            className="flex items-center gap-2 text-xs font-mono text-txt-muted hover:text-txt-main transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>New Analysis</span>
          </button>
          <span className="text-xs font-mono text-txt-dim">Analysis ID: {record.analysis_id}</span>
        </div>

        <UploadProgress
          status={record.status}
          filename={record.audio.filename}
          onCancel={() => navigate('/analyze')}
        />
      </div>
    );
  }

  // Failed state
  if (record.status === 'failed') {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <button
            onClick={() => navigate('/analyze')}
            className="flex items-center gap-2 text-xs font-mono text-txt-muted hover:text-txt-main transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>New Analysis</span>
          </button>
        </div>

        <UploadProgress
          status="failed"
          filename={record.audio.filename}
          errorMessage={getHumanReadableErrorMessage(record.error_code, record.error_message)}
          onRetry={() => navigate('/analyze')}
        />
      </div>
    );
  }

  // Completed Analyst Report Screen
  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Navigation Top Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 font-mono text-xs">
        <Link
          to="/history"
          className="flex items-center gap-1.5 text-txt-muted hover:text-txt-main transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Evaluation History</span>
        </Link>

        <div className="flex items-center gap-3 text-txt-dim">
          <span>Report ID: <code className="text-txt-muted">{record.analysis_id}</code></span>
          <span>·</span>
          <span>Created: {new Date(record.created_at).toLocaleTimeString()}</span>
        </div>
      </div>

      {/* 1. Verdict Hero Section */}
      <VerdictHero
        verdict={record.verdict}
        filename={record.audio.filename}
        durationSeconds={record.audio.duration_seconds}
        format={record.audio.format}
        language={record.audio.language}
      />

      {/* 2. Synthetic Probability Horizontal Linear Scale */}
      <ProbabilityScale
        probability={record.synthetic_probability}
        confidence={record.confidence}
        verdict={record.verdict}
        lowThreshold={record.evidence?.low_threshold}
        highThreshold={record.evidence?.high_threshold}
      />

      {/* 3. Audio Player with Timeline Anomaly Highlights */}
      <AudioPlayer
        src={record.audio.audio_url}
        filename={record.audio.filename}
        flaggedRanges={record.evidence?.flagged_time_ranges}
      />

      {/* 4. Progressive Disclosure Evidence Panel */}
      <EvidenceDrawer evidence={record.evidence} defaultOpen={true} />

      {/* 5. High-Density Technical Metadata Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <AudioMetadata metadata={record.audio} />
        <ModelMetadata model={record.model} />
      </div>
    </div>
  );
};
