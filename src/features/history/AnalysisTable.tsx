import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AnalysisRecord } from '../../types/api';
import { VerdictBadge } from '../../components/VerdictBadge';
import { formatDate, formatBytes } from '../../lib/utils';
import { FileAudio, Trash2, ArrowRight, Clock, AlertCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

interface AnalysisTableProps {
  records: AnalysisRecord[];
  onDeleteRequest: (record: AnalysisRecord) => void;
}

export const AnalysisTable: React.FC<AnalysisTableProps> = ({
  records,
  onDeleteRequest,
}) => {
  const navigate = useNavigate();

  if (records.length === 0) {
    return (
      <div className="rounded-lg border border-border-strong bg-bg-surface p-12 text-center space-y-3 shadow-panel">
        <div className="w-12 h-12 rounded-full bg-bg-surface-elevated border border-border-subtle flex items-center justify-center text-txt-dim mx-auto">
          <FileAudio className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-semibold text-txt-main">No audio evaluations found</h4>
        <p className="text-xs font-mono text-txt-muted max-w-sm mx-auto">
          Upload an audio recording on the workspace page to generate your first technical report.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border-strong bg-bg-surface overflow-hidden shadow-panel">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-border-subtle bg-bg-surface-elevated/50 text-[11px] font-mono uppercase tracking-wider text-txt-dim select-none">
              <th className="py-3 px-4 font-semibold">Audio Recording</th>
              <th className="py-3 px-4 font-semibold">Verdict</th>
              <th className="py-3 px-4 font-semibold text-right">Synthetic Prob.</th>
              <th className="py-3 px-4 font-semibold">Evaluation Date</th>
              <th className="py-3 px-4 font-semibold">Status</th>
              <th className="py-3 px-4 font-semibold text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle text-xs font-mono">
            {records.map((rec) => {
              const probPct = rec.synthetic_probability !== null ? (rec.synthetic_probability * 100).toFixed(1) : '--';

              return (
                <tr
                  key={rec.analysis_id}
                  onClick={() => navigate(`/analysis/${rec.analysis_id}`)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      navigate(`/analysis/${rec.analysis_id}`);
                    }
                  }}
                  className="group hover:bg-bg-surface-hover transition-colors cursor-pointer outline-none focus-visible:bg-bg-surface-hover"
                >
                  {/* File Column */}
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded bg-bg-surface-elevated border border-border-subtle text-brand group-hover:border-brand/40 transition-colors">
                        <FileAudio className="w-4 h-4" />
                      </div>
                      <div className="space-y-0.5 max-w-xs truncate">
                        <span className="font-semibold text-txt-main group-hover:text-brand transition-colors block truncate">
                          {rec.audio.filename}
                        </span>
                        <div className="flex items-center gap-1.5 text-[11px] text-txt-dim">
                          <span>{rec.audio.format}</span>
                          <span>·</span>
                          <span>{formatBytes(rec.audio.file_size_bytes)}</span>
                          {rec.audio.language && (
                            <>
                              <span>·</span>
                              <span className="uppercase">{rec.audio.language}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Verdict Column */}
                  <td className="py-3 px-4">
                    <VerdictBadge verdict={rec.verdict} size="sm" />
                  </td>

                  {/* Probability Column */}
                  <td className="py-3 px-4 text-right font-bold text-txt-main">
                    {rec.synthetic_probability !== null ? (
                      <span className={cn(
                        rec.verdict === 'likely_synthetic' ? 'text-rose-400' :
                        rec.verdict === 'consistent_with_human' ? 'text-emerald-400' :
                        'text-amber-400'
                      )}>
                        {probPct}%
                      </span>
                    ) : (
                      <span className="text-txt-dim">--</span>
                    )}
                  </td>

                  {/* Date Column */}
                  <td className="py-3 px-4 text-txt-muted">
                    {formatDate(rec.created_at)}
                  </td>

                  {/* Status Column */}
                  <td className="py-3 px-4">
                    {rec.status === 'completed' && (
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-semibold">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                        Completed
                      </span>
                    )}
                    {rec.status === 'processing' && (
                      <span className="inline-flex items-center gap-1 text-[11px] text-brand font-semibold animate-pulse">
                        <Clock className="w-3 h-3" />
                        Processing
                      </span>
                    )}
                    {rec.status === 'queued' && (
                      <span className="inline-flex items-center gap-1 text-[11px] text-amber-400 font-semibold">
                        <Clock className="w-3 h-3" />
                        Queued
                      </span>
                    )}
                    {rec.status === 'failed' && (
                      <span className="inline-flex items-center gap-1 text-[11px] text-rose-400 font-semibold">
                        <AlertCircle className="w-3 h-3" />
                        Failed
                      </span>
                    )}
                  </td>

                  {/* Action Column */}
                  <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => navigate(`/analysis/${rec.analysis_id}`)}
                        className="p-1.5 rounded text-txt-muted hover:text-brand hover:bg-bg-surface-elevated transition-colors"
                        title="View Report"
                      >
                        <ArrowRight className="w-4 h-4" />
                      </button>

                      <button
                        onClick={() => onDeleteRequest(rec)}
                        className="p-1.5 rounded text-txt-muted hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                        title="Delete Evaluation Record"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
