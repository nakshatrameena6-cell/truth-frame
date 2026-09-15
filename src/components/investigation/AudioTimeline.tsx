import React, { useRef } from 'react';
import { SuspiciousSection } from '../../types/investigation';
import { formatTimeSeconds } from '../../lib/investigationMapper';

interface AudioTimelineProps {
  currentTime: number;
  duration: number;
  suspiciousSections: SuspiciousSection[];
  activeSectionId: string | null;
  onSeek: (seconds: number) => void;
  onSelectSection?: (section: SuspiciousSection) => void;
}

export const AudioTimeline: React.FC<AudioTimelineProps> = ({
  currentTime,
  duration,
  suspiciousSections,
  activeSectionId,
  onSeek,
  onSelectSection,
}) => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const safeDuration = duration > 0 ? duration : 1;

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timelineRef.current) return;
    const rect = timelineRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, clickX / rect.width));
    onSeek(ratio * safeDuration);
  };

  // Generate deterministic waveform-like bars for visual feedback
  const barCount = 70;
  const bars = React.useMemo(() => {
    return Array.from({ length: barCount }, (_, i) => {
      // Deterministic pseudo-waveform pattern
      const angle = (i / barCount) * Math.PI * 6;
      const height = 25 + Math.abs(Math.sin(angle) * 45) + Math.abs(Math.cos(angle * 2.3) * 20);
      return Math.min(95, Math.max(20, height));
    });
  }, [barCount]);

  const progressPercent = (currentTime / safeDuration) * 100;

  return (
    <div className="space-y-2 select-none">
      {/* Visual Timeline Track */}
      <div
        ref={timelineRef}
        onClick={handleTimelineClick}
        className="relative h-16 w-full bg-bg-surface-elevated rounded-lg border border-border-subtle cursor-pointer overflow-hidden group"
        role="slider"
        aria-label="Audio timeline with flagged suspicious speech sections"
        aria-valuemin={0}
        aria-valuemax={safeDuration}
        aria-valuenow={currentTime}
      >
        {/* Synthetic Suspicious Segments Overlays */}
        {suspiciousSections.map((section) => {
          const leftPercent = (section.startSeconds / safeDuration) * 100;
          const widthPercent = Math.max(
            1.5,
            ((section.endSeconds - section.startSeconds) / safeDuration) * 100
          );
          const isSelected = activeSectionId === section.id;

          return (
            <div
              key={section.id}
              onClick={(e) => {
                e.stopPropagation();
                onSeek(section.startSeconds);
                if (onSelectSection) onSelectSection(section);
              }}
              style={{
                left: `${leftPercent}%`,
                width: `${widthPercent}%`,
              }}
              className={`absolute top-0 bottom-0 z-10 transition-all cursor-pointer ${
                isSelected
                  ? 'bg-rose-500/40 border-x-2 border-rose-500 ring-2 ring-rose-500/50'
                  : 'bg-rose-500/25 hover:bg-rose-500/35 border-x border-rose-400/60'
              }`}
              title={`Suspicious speech section: ${section.startFormatted} - ${section.endFormatted} (${section.confidencePercent}% confidence)`}
            >
              {/* Top Section Tag Indicator */}
              <div className="absolute top-1 left-1/2 -translate-x-1/2 px-1.5 py-0.5 rounded bg-rose-600 text-[9px] font-mono text-white font-bold tracking-tight shadow-sm whitespace-nowrap pointer-events-none">
                {section.confidencePercent}%
              </div>
            </div>
          );
        })}

        {/* Pseudo Waveform Bars */}
        <div className="absolute inset-0 flex items-center justify-between px-2 gap-[2px] opacity-75">
          {bars.map((height, i) => {
            const barPercent = (i / barCount) * 100;
            const isPlayed = barPercent <= progressPercent;

            return (
              <div
                key={i}
                style={{ height: `${height}%` }}
                className={`w-full rounded-full transition-colors ${
                  isPlayed
                    ? 'bg-brand'
                    : 'bg-txt-dim/30 group-hover:bg-txt-dim/40'
                }`}
              />
            );
          })}
        </div>

        {/* Scrubber Playhead Line */}
        <div
          style={{ left: `${Math.min(100, Math.max(0, progressPercent))}%` }}
          className="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_8px_rgba(255,255,255,0.8)] z-20 pointer-events-none transition-[left] duration-75"
        >
          <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-white shadow-md border border-brand" />
        </div>
      </div>

      {/* Timeline Time Indices */}
      <div className="flex justify-between items-center text-xs font-mono text-txt-dim px-1">
        <span>00:00.00</span>
        <span className="text-txt-muted font-medium">
          {formatTimeSeconds(currentTime)} / {formatTimeSeconds(safeDuration)}
        </span>
        <span>{formatTimeSeconds(safeDuration)}</span>
      </div>
    </div>
  );
};
