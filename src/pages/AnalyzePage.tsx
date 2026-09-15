import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AudioUploader } from '../components/investigation/AudioUploader';
import { AnalysisProgress, ProgressStep } from '../components/investigation/AnalysisProgress';
import { MOCK_SCENARIOS, MOCK_HISTORY_REPORTS } from '../lib/mockScenarios';
import { InvestigationReport } from '../types/investigation';
import { ShieldCheck, ArrowLeft } from 'lucide-react';

export const AnalyzePage: React.FC = () => {
  const navigate = useNavigate();
  const [isAnalysing, setIsAnalysing] = useState(false);
  const [currentStep, setCurrentStep] = useState<ProgressStep>('received');
  const [analyzingFilename, setAnalyzingFilename] = useState('');

  const handleSubmit = (
    file: File | null,
    caseReference?: string,
    scenarioId?: string
  ) => {
    // If a predefined scenario was selected:
    if (scenarioId && scenarioId in MOCK_SCENARIOS) {
      navigate(`/analysis/${scenarioId}`);
      return;
    }

    const filename = file?.name || 'customer_call.wav';
    setAnalyzingFilename(filename);
    setIsAnalysing(true);
    setCurrentStep('received');

    // Simulate the human-readable step progression smoothly:
    // ✓ Recording received -> ✓ Recording quality reviewed -> ● Analysing speech -> ○ Preparing result
    setTimeout(() => {
      setCurrentStep('quality_reviewed');
    }, 900);

    setTimeout(() => {
      setCurrentStep('analysing_speech');
    }, 1900);

    setTimeout(() => {
      setCurrentStep('preparing_result');
    }, 3100);

    setTimeout(() => {
      // Create new investigation report from uploaded file
      const newId = `case-eval-${Date.now().toString().slice(-4)}`;
      const newReport: InvestigationReport = {
        id: newId,
        caseReference: caseReference || `CASE-${Date.now().toString().slice(-4)}`,
        recordingName: filename,
        fileSizeBytes: file?.size || 3420000,
        fileSizeFormatted: file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB` : '3.26 MB',
        durationSeconds: 16.4,
        durationFormatted: '16s',
        createdAt: new Date().toISOString(),
        createdAtFormatted: 'Just now',
        result: 'likely_synthetic',
        confidencePercent: 88,
        summary:
          'The recording contains acoustic characteristics consistent with synthetic or cloned speech.',
        suspiciousSections: [
          {
            id: 'sec-1',
            startSeconds: 3.4,
            endSeconds: 6.2,
            startFormatted: '00:03.40',
            endFormatted: '00:06.20',
            confidencePercent: 93,
            label: 'Synthetic voice synthesis artifact',
            evidenceSummary:
              'Neural vocoder phase discontinuity detected during vocalization burst.',
          },
        ],
        evidenceCategories: [
          {
            id: 'ev-1',
            name: 'Speech characteristics',
            scorePercent: 88,
            bias: 'synthetic',
            explanation:
              'High-frequency harmonics exhibit unnatural mathematical regularity consistent with neural voice synthesis.',
          },
          {
            id: 'ev-2',
            name: 'Voice pattern consistency',
            scorePercent: 76,
            bias: 'synthetic',
            explanation:
              'Vocal tract resonance transitions deviate from biological physical constraints.',
          },
          {
            id: 'ev-3',
            name: 'Timing and rhythm',
            scorePercent: 62,
            bias: 'synthetic',
            explanation:
              'Cadence intervals show reduced micro-timing variation typical of automated generation.',
          },
        ],
        conditions: {
          overallQuality: 'Good',
          speechAvailableDuration: '16.4 seconds',
          speechAvailableSeconds: 16.4,
          clarity: 'High',
          recordingType: 'Clean',
          sampleRateFormatted: '24.0 kHz',
          channelsFormatted: 'Mono (1 channel)',
          format: file?.name.split('.').pop()?.toUpperCase() || 'WAV',
          notes: 'Direct acoustic capture with adequate signal strength.',
        },
        language: {
          detected: 'Hindi + English',
          isCodeSwitching: true,
          codeSwitchingDetails: 'Code-switching detected',
          isSupported: true,
        },
        provenance: {
          digitalCredentials: 'Not available',
          audioWatermark: 'Not detected',
          advisoryNote:
            'The absence of these credentials does not by itself indicate synthetic audio.',
        },
      };

      // Push into mock reports cache
      MOCK_HISTORY_REPORTS.unshift(newReport);

      setIsAnalysing(false);
      navigate(`/analysis/${newId}`);
    }, 4200);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-4 animate-in fade-in duration-150">
      {/* Page Header */}
      <div className="border-b border-border-subtle pb-4">
        <h1 className="text-2xl font-bold tracking-tight text-txt-main">
          New Analysis
        </h1>
        <p className="text-sm text-txt-muted mt-1 leading-relaxed">
          Upload a call recording to assess whether the voice is consistent with genuine human speech.
        </p>
      </div>

      {/* Main Upload or Progress State */}
      {isAnalysing ? (
        <div className="py-12">
          <AnalysisProgress
            filename={analyzingFilename}
            currentStep={currentStep}
            onCancel={() => setIsAnalysing(false)}
          />
        </div>
      ) : (
        <AudioUploader onSubmit={handleSubmit} isLoading={isAnalysing} />
      )}

      {/* Bottom Compliance & Guidance Note */}
      <div className="pt-4 border-t border-border-subtle text-xs text-txt-dim space-y-1 font-mono">
        <div className="flex items-center gap-2 text-txt-muted">
          <ShieldCheck className="w-4 h-4 text-emerald-500" />
          <span>Strict Enterprise Confidentiality</span>
        </div>
        <p>
          Recordings submitted are evaluated exclusively within this secure investigation session in accordance with institutional governance policies.
        </p>
      </div>
    </div>
  );
};
