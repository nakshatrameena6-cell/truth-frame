import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, RotateCcw, ShieldAlert } from 'lucide-react';
import { formatDuration } from '../../lib/utils';
import { FlaggedTimeRange } from '../../types/api';
import { cn } from '../../lib/utils';

interface AudioPlayerProps {
  src?: string;
  filename: string;
  flaggedRanges?: FlaggedTimeRange[];
  className?: string;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({
  src,
  filename,
  flaggedRanges = [],
  className,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const progressBarRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(console.error);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!progressBarRef.current || !audioRef.current || !duration) return;
    const rect = progressBarRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const width = rect.width;
    const seekTime = (clickX / width) * duration;
    audioRef.current.currentTime = seekTime;
    setCurrentTime(seekTime);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.code === 'Space') {
      e.preventDefault();
      togglePlay();
    } else if (e.code === 'ArrowRight') {
      e.preventDefault();
      if (audioRef.current) {
        audioRef.current.currentTime = Math.min(duration, audioRef.current.currentTime + 5);
      }
    } else if (e.code === 'ArrowLeft') {
      e.preventDefault();
      if (audioRef.current) {
        audioRef.current.currentTime = Math.max(0, audioRef.current.currentTime - 5);
      }
    }
  };

  return (
    <div
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className={cn(
        'rounded-lg border border-border-strong bg-bg-surface p-5 space-y-4 shadow-panel outline-none focus-visible:border-brand',
        className
      )}
      aria-label={`Audio Player for ${filename}`}
    >
      <audio
        ref={audioRef}
        src={src}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={() => setIsPlaying(false)}
      />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold text-txt-main">Audio Inspection Player</span>
          <span className="text-[10px] font-mono text-txt-dim px-1.5 py-0.5 rounded bg-bg-surface-elevated border border-border-subtle">
            Focus + Space to Play/Pause
          </span>
        </div>
        <div className="text-xs font-mono text-txt-muted">
          <span>{formatDuration(currentTime)}</span>
          <span className="mx-1 text-txt-dim">/</span>
          <span>{formatDuration(duration)}</span>
        </div>
      </div>

      {/* Scrubbable Timeline Track with Highlighted Evidence Ranges */}
      <div className="space-y-1.5">
        <div
          ref={progressBarRef}
          onClick={handleSeek}
          className="relative h-4 w-full rounded bg-bg-surface-elevated border border-border-subtle cursor-pointer overflow-hidden group"
        >
          {/* Flagged Time Range Overlays */}
          {duration > 0 &&
            flaggedRanges.map((range, idx) => {
              const leftPct = (range.start_time / duration) * 100;
              const widthPct = ((range.end_time - range.start_time) / duration) * 100;
              return (
                <div
                  key={idx}
                  className="absolute top-0 bottom-0 bg-rose-500/25 border-x border-rose-500/40 z-10"
                  style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                  title={`Flagged Anomaly Segment: ${range.start_time.toFixed(1)}s - ${range.end_time.toFixed(1)}s (${range.label})`}
                />
              );
            })}

          {/* Current Played Progress Fill */}
          <div
            className="h-full bg-brand/80 group-hover:bg-brand transition-all rounded-sm"
            style={{ width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }}
          />
        </div>

        {/* Highlighted Evidence Legend */}
        {flaggedRanges.length > 0 && (
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-rose-400">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>
              {flaggedRanges.length} acoustic anomaly region(s) highlighted on timeline
            </span>
          </div>
        )}
      </div>

      {/* Player Controls Bar */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-2">
          <button
            onClick={togglePlay}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-brand hover:bg-brand-hover text-white text-xs font-mono font-semibold transition-colors shadow-subtle"
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isPlaying ? 'Pause' : 'Play'}</span>
          </button>

          <button
            onClick={() => {
              if (audioRef.current) audioRef.current.currentTime = 0;
            }}
            className="p-1.5 rounded bg-bg-surface-elevated border border-border-subtle text-txt-muted hover:text-txt-main transition-colors"
            title="Reset to beginning"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Volume Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsMuted(!isMuted)}
            className="text-txt-muted hover:text-txt-main p-1 rounded"
          >
            {isMuted || volume === 0 ? (
              <VolumeX className="w-4 h-4 text-rose-400" />
            ) : (
              <Volume2 className="w-4 h-4 text-txt-muted" />
            )}
          </button>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={isMuted ? 0 : volume}
            onChange={(e) => {
              setVolume(parseFloat(e.target.value));
              setIsMuted(false);
            }}
            className="w-20 accent-brand cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
};
