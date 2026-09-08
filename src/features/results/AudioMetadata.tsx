import React from 'react';
import { AudioMetadata as AudioMetadataType } from '../../types/api';
import { formatBytes } from '../../lib/utils';

interface AudioMetadataProps {
  metadata: AudioMetadataType;
}

export const AudioMetadata: React.FC<AudioMetadataProps> = ({ metadata }) => {
  const items = [
    { label: 'Filename', value: metadata.filename },
    { label: 'Format', value: metadata.format },
    { label: 'File Size', value: formatBytes(metadata.file_size_bytes) },
    { label: 'Duration', value: `${metadata.duration_seconds.toFixed(1)} seconds` },
    { label: 'Sample Rate', value: `${metadata.sample_rate} Hz` },
    { label: 'Channels', value: metadata.channels === 1 ? '1 (Mono)' : `${metadata.channels} (Stereo)` },
    { label: 'Language', value: metadata.language ? metadata.language.toUpperCase() : 'Unspecified' },
    { label: 'Degradation', value: metadata.degradation || 'Clean' },
  ];

  return (
    <div className="rounded-lg border border-border-strong bg-bg-surface p-5 space-y-3 shadow-panel">
      <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-txt-dim pb-2 border-b border-border-subtle">
        Audio Stream Metadata
      </h4>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        {items.map((item) => (
          <div key={item.label} className="p-2.5 rounded bg-bg-surface-elevated border border-border-subtle space-y-0.5">
            <span className="text-[10px] text-txt-dim block uppercase">{item.label}</span>
            <span className="font-medium text-txt-main truncate block">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
