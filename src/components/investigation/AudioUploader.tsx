import React, { useState, useRef } from 'react';
import { UploadCloud, FileAudio, AlertCircle, Check, ArrowRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import { formatFileSizeBytes } from '../../lib/investigationMapper';

const SUPPORTED_EXTENSIONS = ['.wav', '.flac', '.mp3', '.ogg', '.opus', '.amr'];
const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // 50 MB
const MAX_DURATION_SECONDS = 600; // 10 minutes

interface AudioUploaderProps {
  onSubmit: (file: File | null, caseReference?: string, scenarioId?: string) => void;
  isLoading?: boolean;
}

export const AudioUploader: React.FC<AudioUploaderProps> = ({
  onSubmit,
  isLoading = false,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [caseReference, setCaseReference] = useState('');
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): boolean => {
    setValidationError(null);

    // Format validation
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    const isSupported = SUPPORTED_EXTENSIONS.includes(ext);
    if (!isSupported) {
      setValidationError(
        `Unsupported file type (${ext}). Please provide audio in WAV, FLAC, MP3, OGG, Opus, or AMR-NB format.`
      );
      return false;
    }

    // Size validation
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setValidationError(
        `File size exceeds 50 MB limit (${formatFileSizeBytes(file.size)}).`
      );
      return false;
    }

    return true;
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (validateFile(file)) {
        setSelectedFile(file);
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (validateFile(file)) {
        setSelectedFile(file);
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setValidationError('Please select or drop an audio recording to analyse.');
      return;
    }
    if (!consentConfirmed) {
      setValidationError(
        'Please confirm that this recording has been submitted for an authorised investigation.'
      );
      return;
    }

    setValidationError(null);
    onSubmit(selectedFile, caseReference.trim() || undefined);
  };

  const handleLoadScenario = (scenarioId: string) => {
    onSubmit(null, caseReference.trim() || undefined, scenarioId);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Validation Error Banner */}
      {validationError && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-start gap-3 text-xs text-rose-400 font-mono">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-500" />
          <div>
            <span className="font-semibold text-rose-300 block">
              Validation Check
            </span>
            <p className="mt-0.5">{validationError}</p>
          </div>
        </div>
      )}

      {/* Large Drag & Drop Upload Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          'relative rounded-xl border-2 border-dashed p-8 md:p-12 text-center cursor-pointer transition-all duration-200 group select-none',
          dragActive
            ? 'border-brand bg-brand/5 scale-[1.005]'
            : selectedFile
            ? 'border-emerald-500/50 bg-emerald-500/5'
            : 'border-border-strong hover:border-brand/60 bg-bg-surface hover:bg-bg-surface-hover'
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".wav,.flac,.mp3,.ogg,.opus,.amr"
          onChange={handleChange}
          className="hidden"
          aria-label="Upload call recording audio file"
        />

        {selectedFile ? (
          <div className="flex flex-col items-center space-y-3">
            <div className="w-14 h-14 rounded-full bg-emerald-500/15 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
              <FileAudio className="w-7 h-7" />
            </div>
            <div>
              <h4 className="text-base font-semibold text-txt-main">
                {selectedFile.name}
              </h4>
              <p className="text-xs font-mono text-txt-dim mt-1">
                {formatFileSizeBytes(selectedFile.size)} · Ready for investigation
              </p>
            </div>
            <span className="text-xs text-brand font-medium group-hover:underline">
              Click or drop another file to replace
            </span>
          </div>
        ) : (
          <div className="flex flex-col items-center space-y-3">
            <div className="w-14 h-14 rounded-full bg-bg-surface-elevated text-brand flex items-center justify-center border border-border-subtle group-hover:scale-105 transition-transform">
              <UploadCloud className="w-7 h-7" />
            </div>
            <div className="space-y-1">
              <h4 className="text-lg font-semibold text-txt-main tracking-tight">
                Drop a recording here
              </h4>
              <p className="text-xs text-txt-muted">
                or <span className="text-brand font-medium underline">browse files</span> from your computer
              </p>
            </div>
            <div className="pt-2 text-xs font-mono text-txt-dim space-y-0.5">
              <p>WAV • FLAC • MP3 • OGG • Opus • AMR-NB</p>
              <p>Maximum 10 minutes / 50 MB</p>
            </div>
          </div>
        )}
      </div>

      {/* Case Reference & Investigation Consent */}
      <div className="space-y-4 bg-bg-surface p-5 rounded-lg border border-border-subtle">
        {/* Case Reference */}
        <div>
          <label
            htmlFor="case-ref"
            className="block text-xs font-medium text-txt-muted uppercase tracking-wider font-mono mb-1.5"
          >
            Case reference <span className="text-txt-dim font-normal">[optional]</span>
          </label>
          <input
            id="case-ref"
            type="text"
            placeholder="e.g. CASE-2026-8821 or Loan Verification #401"
            value={caseReference}
            onChange={(e) => setCaseReference(e.target.value)}
            className="w-full px-3.5 py-2.5 rounded-md bg-bg-surface-elevated border border-border-subtle text-sm text-txt-main placeholder:text-txt-dim focus:outline-none focus:ring-1 focus:ring-brand font-mono"
          />
        </div>

        {/* Mandatory Legal Consent Checkbox */}
        <div className="pt-2 border-t border-border-subtle/70">
          <label className="flex items-start gap-3 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={consentConfirmed}
              onChange={(e) => setConsentConfirmed(e.target.checked)}
              className="mt-1 w-4 h-4 rounded border-border-strong text-brand focus:ring-brand accent-brand cursor-pointer"
            />
            <span className="text-xs text-txt-muted leading-relaxed">
              I confirm that this recording has been submitted for an authorised investigation.
            </span>
          </label>
        </div>
      </div>

      {/* Submit Button */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <button
          type="submit"
          disabled={isLoading}
          className="px-6 py-3 rounded-lg bg-brand hover:bg-brand-hover text-white font-semibold text-sm shadow-subtle flex items-center justify-center gap-2 transition-all disabled:opacity-50 active:scale-[0.99]"
        >
          <span>Analyse Recording</span>
          <ArrowRight className="w-4 h-4" />
        </button>

        {/* Instant Mock Scenario Test Buttons */}
        <div className="flex items-center gap-2 flex-wrap text-xs font-mono text-txt-dim">
          <span>Or load benchmark case:</span>
          <button
            type="button"
            onClick={() => handleLoadScenario('scenario-a')}
            className="px-2.5 py-1 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-colors"
            title="Load Scenario A: Likely Synthetic (87% confidence, Hindi+English, 2 suspicious sections)"
          >
            A: Synthetic
          </button>
          <button
            type="button"
            onClick={() => handleLoadScenario('scenario-b')}
            className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors"
            title="Load Scenario B: Consistent with Human (92% confidence, Tamil)"
          >
            B: Human
          </button>
          <button
            type="button"
            onClick={() => handleLoadScenario('scenario-c')}
            className="px-2.5 py-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-colors"
            title="Load Scenario C: Inconclusive (Insufficient clear speech, abstention)"
          >
            C: Inconclusive
          </button>
          <button
            type="button"
            onClick={() => handleLoadScenario('scenario-d')}
            className="px-2.5 py-1 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 hover:bg-purple-500/20 transition-colors"
            title="Load Scenario D: Difficult recording (65% confidence, noise)"
          >
            D: Difficult
          </button>
        </div>
      </div>
    </form>
  );
};
