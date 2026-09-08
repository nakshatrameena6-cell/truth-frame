import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createAnalysis, listAnalyses } from '../api/analyses';
import { getAudioFormats } from '../api/formats';
import { AudioDropzone } from '../features/upload/AudioDropzone';
import { AudioRecorder } from '../features/upload/AudioRecorder';
import { UploadProgress } from '../features/upload/UploadProgress';
import { VerdictBadge } from '../components/VerdictBadge';
import { getHumanReadableErrorMessage } from '../lib/errors';
import { formatDate } from '../lib/utils';
import { AudioLines, ShieldCheck, History, ArrowRight, Mic, Upload, FileAudio } from 'lucide-react';
import { cn } from '../lib/utils';

export const AnalyzePage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<'upload' | 'record'>('upload');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('en');
  const [activeAnalysisId, setActiveAnalysisId] = useState<string | null>(null);
  const [activeFilename, setActiveFilename] = useState<string>('');

  // Fetch supported formats
  const { data: formats } = useQuery({
    queryKey: ['audioFormats'],
    queryFn: getAudioFormats,
  });

  // Fetch recent analyses for shortcuts
  const { data: recentAnalyses } = useQuery({
    queryKey: ['analyses'],
    queryFn: listAnalyses,
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: createAnalysis,
    onSuccess: (data) => {
      setActiveAnalysisId(data.analysis_id);
      setActiveFilename(data.audio.filename);
      queryClient.invalidateQueries({ queryKey: ['analyses'] });
      // Navigate directly to result report page where real-time polling will handle processing state
      navigate(`/analysis/${data.analysis_id}`);
    },
  });

  const handleFileSubmitted = (file: File) => {
    setActiveFilename(file.name);
    uploadMutation.mutate({
      audio: file,
      filename: file.name,
      language: selectedLanguage,
      source: 'web_workspace',
    });
  };

  const completedRecent = recentAnalyses
    ?.filter((a) => a.status === 'completed')
    .slice(0, 3);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Page Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold font-mono tracking-tight text-txt-main">
            Audio Evaluation Workspace
          </h1>
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-brand/10 text-brand border border-brand/20">
            Phase 9 Active
          </span>
        </div>
        <p className="text-xs text-txt-muted font-sans max-w-2xl leading-relaxed">
          Submit an audio recording for acoustic feature extraction, volume-normalized spectrogram evaluation, and backend operating point calibration.
        </p>
      </div>

      {/* Upload/Record Workspace Container */}
      <div className="space-y-4">
        {/* Workspace Instrument Header Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg border border-border-strong bg-bg-surface shadow-subtle">
          
          {/* Mode Switcher */}
          <div className="flex items-center gap-1 bg-bg-surface-elevated p-1 rounded border border-border-subtle">
            <button
              onClick={() => setActiveTab('upload')}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded text-xs font-mono font-medium transition-colors',
                activeTab === 'upload'
                  ? 'bg-bg-surface text-brand font-semibold shadow-subtle border border-border-subtle'
                  : 'text-txt-muted hover:text-txt-main'
              )}
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload File</span>
            </button>

            <button
              onClick={() => setActiveTab('record')}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded text-xs font-mono font-medium transition-colors',
                activeTab === 'record'
                  ? 'bg-bg-surface text-brand font-semibold shadow-subtle border border-border-subtle'
                  : 'text-txt-muted hover:text-txt-main'
              )}
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Record Live Speech</span>
            </button>
          </div>

          {/* Language Selection Config */}
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-txt-dim">Target Language:</span>
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="px-2.5 py-1.5 rounded bg-bg-surface-elevated border border-border-subtle text-txt-main text-xs font-mono focus:outline-none focus:border-brand"
            >
              <option value="en">English (en)</option>
              <option value="hi">Hindi (hi)</option>
              <option value="ta">Tamil (ta)</option>
              <option value="hinglish">Hinglish</option>
            </select>
          </div>
        </div>

        {/* Active Upload/Record Panel */}
        {uploadMutation.isPending ? (
          <UploadProgress
            status="uploading"
            filename={activeFilename}
            onCancel={() => uploadMutation.reset()}
          />
        ) : uploadMutation.isError ? (
          <div className="space-y-4">
            <UploadProgress
              status="failed"
              filename={activeFilename}
              errorMessage={getHumanReadableErrorMessage(
                (uploadMutation.error as any)?.error_code,
                (uploadMutation.error as any)?.message
              )}
              onRetry={() => uploadMutation.reset()}
            />
          </div>
        ) : activeTab === 'upload' ? (
          <AudioDropzone
            onFileSelect={handleFileSubmitted}
            supportedExtensions={formats?.supported_extensions}
            maxSizeBytes={formats?.max_file_size_bytes}
          />
        ) : (
          <AudioRecorder onRecorded={handleFileSubmitted} />
        )}
      </div>

      {/* Recent Evaluations Shortcut Carousel */}
      {completedRecent && completedRecent.length > 0 && (
        <div className="space-y-3 pt-4 border-t border-border-subtle">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="font-semibold text-txt-dim uppercase tracking-wider flex items-center gap-1.5">
              <History className="w-3.5 h-3.5 text-brand" />
              <span>Recent Audio Evaluations</span>
            </span>
            <button
              onClick={() => navigate('/history')}
              className="text-brand hover:underline flex items-center gap-1"
            >
              <span>View All History</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {completedRecent.map((item) => (
              <div
                key={item.analysis_id}
                onClick={() => navigate(`/analysis/${item.analysis_id}`)}
                className="p-3 rounded-lg border border-border-strong bg-bg-surface hover:bg-bg-surface-hover hover:border-brand/40 transition-all cursor-pointer space-y-2 shadow-subtle group"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 truncate">
                    <FileAudio className="w-4 h-4 text-brand shrink-0" />
                    <span className="text-xs font-mono font-semibold text-txt-main truncate group-hover:text-brand transition-colors">
                      {item.audio.filename}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] font-mono text-txt-muted pt-1 border-t border-border-subtle">
                  <VerdictBadge verdict={item.verdict} size="sm" showIcon={false} />
                  <span>{formatDate(item.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
