import React, { useState } from 'react';
import { InvestigationReport, SuspiciousSection } from '../../types/investigation';
import { VerdictCard } from './VerdictCard';
import { ConfidenceIndicator } from './ConfidenceIndicator';
import { AudioPlayer } from './AudioPlayer';
import { SuspiciousSectionsList } from './SuspiciousSectionsList';
import { EvidencePanel } from './EvidencePanel';
import { ConditionsCard } from './ConditionsCard';
import { LanguageCard } from './LanguageCard';
import { RecordingInfo } from './RecordingInfo';
import { ArrowLeft, Download, Share2, Shield, Calendar, Clock, FileAudio } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

interface AnalysisResultProps {
  report: InvestigationReport;
  onBack?: () => void;
}

export const AnalysisResult: React.FC<AnalysisResultProps> = ({ report, onBack }) => {
  const navigate = useNavigate();
  const [activeSectionId, setActiveSectionId] = useState<string | null>(
    report.suspiciousSections.length > 0 ? report.suspiciousSections[0].id : null
  );
  const [seekRequestedSeconds, setSeekRequestedSeconds] = useState<number | null>(null);

  const handleSelectSection = (section: SuspiciousSection) => {
    setActiveSectionId(section.id);
    setSeekRequestedSeconds(section.startSeconds);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12 animate-in fade-in duration-200">
      {/* Top Breadcrumb & Metadata Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle pb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack || (() => navigate('/history'))}
            className="flex items-center gap-1.5 text-xs font-mono text-txt-muted hover:text-txt-main transition-colors px-2.5 py-1.5 rounded-md hover:bg-bg-surface-hover border border-border-subtle"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </button>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-brand uppercase tracking-wider">
                {report.caseReference || 'UNASSIGNED CASE'}
              </span>
              <span className="text-txt-dim text-xs">·</span>
              <h1 className="text-sm font-semibold text-txt-main">
                Audio Investigation Report
              </h1>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-bg-surface-elevated border border-border-subtle text-xs font-mono text-txt-muted hover:text-txt-main transition-colors"
            title="Print or Export Case Summary"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Case</span>
          </button>
        </div>
      </div>

      {/* Case Header Details Banner */}
      <div className="bg-bg-surface p-4 rounded-lg border border-border-subtle flex flex-wrap items-center justify-between gap-4 text-xs font-mono text-txt-muted">
        <div className="flex items-center gap-2">
          <FileAudio className="w-4 h-4 text-brand" />
          <span className="font-semibold text-txt-main">{report.recordingName}</span>
          <span className="text-txt-dim">({report.fileSizeFormatted} · {report.durationFormatted})</span>
        </div>

        <div className="flex items-center gap-4 text-txt-dim">
          <div className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5" />
            <span>{report.createdAtFormatted}</span>
          </div>
          <div className="flex items-center gap-1">
            <Shield className="w-3.5 h-3.5 text-emerald-500" />
            <span>Bank Investigation Portal</span>
          </div>
        </div>
      </div>

      {/* 
        PRD MANDATED EXACT HIERARCHY:
        1. RESULT
        2. CONFIDENCE
        3. SUMMARY
        4. AUDIO PLAYER
        5. SUSPICIOUS SECTIONS
        6. WHY THIS RESULT?
        7. RECORDING CONDITIONS
        8. LANGUAGE
        9. RECORDING INFORMATION
      */}

      {/* 1. RESULT */}
      <section aria-labelledby="section-verdict">
        <VerdictCard result={report.result} />
      </section>

      {/* 2. CONFIDENCE */}
      <section aria-labelledby="section-confidence">
        <ConfidenceIndicator
          result={report.result}
          confidencePercent={report.confidencePercent}
        />
      </section>

      {/* 3. SUMMARY */}
      <section
        aria-labelledby="section-summary"
        className="p-4 rounded-lg bg-bg-surface border border-border-subtle space-y-1"
      >
        <span className="text-xs font-semibold uppercase tracking-wider text-txt-muted font-mono">
          Executive Summary
        </span>
        <p className="text-sm text-txt-main leading-relaxed">
          {report.summary}
        </p>
      </section>

      {/* 4. AUDIO PLAYER */}
      <section aria-labelledby="section-audio-player">
        <AudioPlayer
          audioUrl={report.audioUrl}
          filename={report.recordingName}
          durationSeconds={report.durationSeconds}
          suspiciousSections={report.suspiciousSections}
          activeSectionId={activeSectionId}
          onSeekRequested={seekRequestedSeconds}
          onSelectSection={handleSelectSection}
        />
      </section>

      {/* 5. SUSPICIOUS SECTIONS (Where in the call & how sure) */}
      <section aria-labelledby="section-suspicious-sections">
        <SuspiciousSectionsList
          sections={report.suspiciousSections}
          activeSectionId={activeSectionId}
          onSelectSection={handleSelectSection}
        />
      </section>

      {/* 6. WHY THIS RESULT? */}
      <section aria-labelledby="section-why-this-result">
        <EvidencePanel categories={report.evidenceCategories} />
      </section>

      {/* 7. RECORDING CONDITIONS */}
      <section aria-labelledby="section-recording-conditions">
        <ConditionsCard conditions={report.conditions} />
      </section>

      {/* 8. LANGUAGE & 9. RECORDING INFORMATION (Two-column layout on desktop) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 8. LANGUAGE */}
        <section aria-labelledby="section-language">
          <LanguageCard language={report.language} />
        </section>

        {/* 9. RECORDING INFORMATION */}
        <section aria-labelledby="section-recording-information">
          <RecordingInfo provenance={report.provenance} />
        </section>
      </div>
    </div>
  );
};
