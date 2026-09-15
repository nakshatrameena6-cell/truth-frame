import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, ShieldAlert, ShieldCheck, HelpCircle, FileAudio, ArrowRight, Sparkles } from 'lucide-react';
import { AnalysisTable } from '../components/investigation/AnalysisTable';
import { MOCK_HISTORY_REPORTS, MOCK_SCENARIOS } from '../lib/mockScenarios';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();

  // Metrics computation
  const totalCount = MOCK_HISTORY_REPORTS.length;
  const syntheticCount = MOCK_HISTORY_REPORTS.filter((r) => r.result === 'likely_synthetic').length;
  const inconclusiveCount = MOCK_HISTORY_REPORTS.filter((r) => r.result === 'inconclusive').length;
  const humanCount = MOCK_HISTORY_REPORTS.filter((r) => r.result === 'consistent_with_human').length;

  return (
    <div className="space-y-8 animate-in fade-in duration-150">
      {/* Top Banner & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-subtle pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-txt-main">
            Audio Trust Overview
          </h1>
          <p className="text-xs text-txt-muted mt-1">
            Enterprise audio authenticity and synthetic speech forensics for fraud analysts
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

      {/* 4 Stat Overview Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Analyses */}
        <div className="p-5 rounded-lg bg-bg-surface border border-border-subtle space-y-1 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-txt-muted uppercase tracking-wider font-mono">
              Total Analyses
            </span>
            <FileAudio className="w-4 h-4 text-txt-dim" />
          </div>
          <div className="text-3xl font-bold font-mono text-txt-main">
            {totalCount}
          </div>
          <p className="text-[11px] text-txt-dim">
            Investigated recordings
          </p>
        </div>

        {/* Likely Synthetic */}
        <div className="p-5 rounded-lg bg-bg-surface border border-rose-500/30 space-y-1 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 bottom-0 left-0 w-1 bg-rose-500" />
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-rose-500 uppercase tracking-wider font-mono">
              Likely Synthetic
            </span>
            <ShieldAlert className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-3xl font-bold font-mono text-txt-main">
            {syntheticCount}
          </div>
          <p className="text-[11px] text-rose-400">
            Acoustic cloning anomalies detected
          </p>
        </div>

        {/* Inconclusive */}
        <div className="p-5 rounded-lg bg-bg-surface border border-amber-500/30 space-y-1 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 bottom-0 left-0 w-1 bg-amber-500" />
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-amber-500 uppercase tracking-wider font-mono">
              Inconclusive
            </span>
            <HelpCircle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-3xl font-bold font-mono text-txt-main">
            {inconclusiveCount}
          </div>
          <p className="text-[11px] text-amber-400">
            Abstained due to degraded audio
          </p>
        </div>

        {/* Consistent with Human */}
        <div className="p-5 rounded-lg bg-bg-surface border border-emerald-500/30 space-y-1 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 bottom-0 left-0 w-1 bg-emerald-500" />
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-500 uppercase tracking-wider font-mono">
              Consistent with Human
            </span>
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-3xl font-bold font-mono text-txt-main">
            {humanCount}
          </div>
          <p className="text-[11px] text-emerald-400">
            Natural vocal acoustics verified
          </p>
        </div>
      </div>

      {/* Quick Test Scenarios Bar */}
      <div className="p-4 rounded-lg bg-bg-surface border border-border-subtle flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-brand" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-txt-main font-mono">
              Quick Investigation Scenarios
            </h3>
          </div>
          <p className="text-xs text-txt-muted">
            Test PRD benchmark cases directly without uploading audio:
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => navigate('/analysis/scenario-a')}
            className="px-3 py-1.5 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/25 text-xs font-mono font-medium transition-colors"
          >
            A: Synthetic (87%)
          </button>
          <button
            onClick={() => navigate('/analysis/scenario-b')}
            className="px-3 py-1.5 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/25 text-xs font-mono font-medium transition-colors"
          >
            B: Human (92%)
          </button>
          <button
            onClick={() => navigate('/analysis/scenario-c')}
            className="px-3 py-1.5 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/25 text-xs font-mono font-medium transition-colors"
          >
            C: Inconclusive
          </button>
          <button
            onClick={() => navigate('/analysis/scenario-d')}
            className="px-3 py-1.5 rounded bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/25 text-xs font-mono font-medium transition-colors"
          >
            D: Difficult Recording
          </button>
        </div>
      </div>

      {/* Recent Analyses Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-txt-main tracking-tight">
              Recent Analyses
            </h2>
            <p className="text-xs text-txt-muted">
              Most recent audio call evaluations logged in this workspace
            </p>
          </div>

          <button
            onClick={() => navigate('/history')}
            className="text-xs font-mono text-brand hover:underline flex items-center gap-1"
          >
            <span>View all in History</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <AnalysisTable reports={MOCK_HISTORY_REPORTS} limit={5} />
      </div>
    </div>
  );
};
