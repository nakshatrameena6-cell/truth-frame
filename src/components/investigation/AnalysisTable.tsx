import React from 'react';
import { InvestigationReport, InvestigationResult } from '../../types/investigation';
import { ShieldCheck, AlertTriangle, HelpCircle, ArrowUpRight, FileAudio } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '../../lib/utils';

interface AnalysisTableProps {
  reports: InvestigationReport[];
  isLoading?: boolean;
  emptyMessage?: string;
  limit?: number;
}

export const AnalysisTable: React.FC<AnalysisTableProps> = ({
  reports,
  isLoading = false,
  emptyMessage = 'No investigations found.',
  limit,
}) => {
  const displayReports = limit ? reports.slice(0, limit) : reports;

  const renderVerdictBadge = (result: InvestigationResult) => {
    switch (result) {
      case 'likely_synthetic':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-500/10 border border-rose-500/25 text-xs font-mono font-semibold text-rose-400">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
            <span>Likely Synthetic</span>
          </span>
        );
      case 'consistent_with_human':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/25 text-xs font-mono font-semibold text-emerald-400">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            <span>Consistent with Human</span>
          </span>
        );
      case 'inconclusive':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/25 text-xs font-mono font-semibold text-amber-400">
            <HelpCircle className="w-3.5 h-3.5 text-amber-500" />
            <span>Inconclusive</span>
          </span>
        );
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center border border-border-subtle bg-bg-surface rounded-lg space-y-3 font-mono text-xs text-txt-muted">
        <div className="w-6 h-6 border-2 border-brand border-t-transparent rounded-full animate-spin mx-auto" />
        <p>Loading investigation records...</p>
      </div>
    );
  }

  if (displayReports.length === 0) {
    return (
      <div className="p-10 text-center border border-dashed border-border-strong bg-bg-surface rounded-lg space-y-2">
        <p className="text-sm font-medium text-txt-muted">{emptyMessage}</p>
        <p className="text-xs text-txt-dim">
          Upload a new call recording to begin an investigation.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border-subtle bg-bg-surface shadow-sm">
      <table className="w-full text-left border-collapse text-xs">
        <thead>
          <tr className="border-b border-border-subtle bg-bg-surface-elevated/50 font-mono text-txt-dim uppercase tracking-wider">
            <th className="py-3 px-4 font-semibold">Case</th>
            <th className="py-3 px-4 font-semibold">Recording</th>
            <th className="py-3 px-4 font-semibold">Result</th>
            <th className="py-3 px-4 font-semibold">Confidence</th>
            <th className="py-3 px-4 font-semibold">Date</th>
            <th className="py-3 px-4 font-semibold text-right">View</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-subtle">
          {displayReports.map((report) => (
            <tr
              key={report.id}
              className="hover:bg-bg-surface-hover/80 transition-colors group"
            >
              {/* Case */}
              <td className="py-3.5 px-4 font-mono font-medium text-txt-main">
                <Link
                  to={`/analysis/${report.id}`}
                  className="hover:text-brand hover:underline transition-colors flex items-center gap-1.5"
                >
                  <span>{report.caseReference || report.id}</span>
                </Link>
              </td>

              {/* Recording */}
              <td className="py-3.5 px-4 font-mono text-txt-muted max-w-[220px]">
                <div className="flex items-center gap-2 truncate" title={report.recordingName}>
                  <FileAudio className="w-3.5 h-3.5 text-txt-dim shrink-0" />
                  <span className="truncate">{report.recordingName}</span>
                </div>
              </td>

              {/* Result */}
              <td className="py-3.5 px-4 whitespace-nowrap">
                {renderVerdictBadge(report.result)}
              </td>

              {/* Confidence */}
              <td className="py-3.5 px-4 font-mono whitespace-nowrap">
                {report.result === 'inconclusive' || report.confidencePercent === null ? (
                  <span className="text-txt-dim text-[11px]">—</span>
                ) : (
                  <span className="font-bold text-txt-main">
                    {report.confidencePercent}%
                  </span>
                )}
              </td>

              {/* Date */}
              <td className="py-3.5 px-4 font-mono text-txt-dim whitespace-nowrap">
                {report.createdAtFormatted}
              </td>

              {/* View Action */}
              <td className="py-3.5 px-4 text-right whitespace-nowrap">
                <Link
                  to={`/analysis/${report.id}`}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-bg-surface-elevated border border-border-subtle hover:border-brand/50 text-txt-muted hover:text-brand text-xs font-mono transition-colors"
                >
                  <span>Open</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
