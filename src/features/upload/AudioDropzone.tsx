import React, { useState, useRef } from 'react';
import { Upload, FileAudio, AlertCircle, Sparkles } from 'lucide-react';
import { formatBytes } from '../../lib/utils';
import { cn } from '../../lib/utils';

interface AudioDropzoneProps {
  onFileSelect: (file: File) => void;
  maxSizeBytes?: number; // Default 25MB
  supportedExtensions?: string[];
  disabled?: boolean;
}

export const AudioDropzone: React.FC<AudioDropzoneProps> = ({
  onFileSelect,
  maxSizeBytes = 26214400,
  supportedExtensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a'],
  disabled = false,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndSelect = (file: File) => {
    setErrorMsg(null);
    const ext = `.${file.name.split('.').pop()?.toLowerCase()}`;
    
    if (!supportedExtensions.includes(ext)) {
      setErrorMsg(`Unsupported audio format (${ext}). Supported formats: ${supportedExtensions.join(', ')}.`);
      return;
    }

    if (file.size > maxSizeBytes) {
      setErrorMsg(`File size (${formatBytes(file.size)}) exceeds maximum limit of ${formatBytes(maxSizeBytes)}.`);
      return;
    }

    onFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      validateAndSelect(file);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSelect(e.target.files[0]);
    }
  };

  return (
    <div className="w-full space-y-3">
      {/* Drop Zone Box */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        tabIndex={disabled ? -1 : 0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            !disabled && fileInputRef.current?.click();
          }
        }}
        className={cn(
          'relative group cursor-pointer rounded-lg border border-dashed transition-all p-8 flex flex-col items-center justify-center text-center select-none outline-none',
          isDragOver
            ? 'border-brand bg-brand-subtle'
            : 'border-border-strong bg-bg-surface hover:bg-bg-surface-hover hover:border-brand/50',
          disabled && 'opacity-50 cursor-not-allowed hover:bg-bg-surface hover:border-border-strong'
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={supportedExtensions.join(',')}
          onChange={handleInputChange}
          className="hidden"
          disabled={disabled}
        />

        {/* Technical Instrument Icon Header */}
        <div className="w-12 h-12 rounded-full bg-bg-surface-elevated border border-border-subtle flex items-center justify-center text-brand mb-3 group-hover:scale-105 transition-transform">
          <Upload className="w-6 h-6" />
        </div>

        <div className="space-y-1">
          <p className="text-sm font-semibold text-txt-main">
            Drop audio file here or <span className="text-brand underline decoration-brand/30 hover:decoration-brand">browse files</span>
          </p>
          <p className="text-xs text-txt-muted font-mono">
            Supported formats: {supportedExtensions.join(', ')} · Max file size: {formatBytes(maxSizeBytes)}
          </p>
        </div>

        {/* Quick sample shortcut suggestion */}
        <div className="mt-4 flex items-center gap-2 px-3 py-1 rounded bg-bg-surface-elevated border border-border-subtle text-[11px] text-txt-dim font-mono">
          <FileAudio className="w-3.5 h-3.5 text-brand" />
          <span>WAV, MP3, FLAC, OGG, M4A up to 5 mins duration</span>
        </div>
      </div>

      {/* Human readable validation error alert */}
      {errorMsg && (
        <div className="flex items-center gap-2 p-3 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-mono animate-in fade-in">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
};
