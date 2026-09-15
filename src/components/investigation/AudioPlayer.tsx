import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, RotateCcw, Volume2, VolumeX, Sparkles } from 'lucide-react';
import { SuspiciousSection } from '../../types/investigation';
import { AudioTimeline } from './AudioTimeline';
import { cn } from '../../lib/utils';

interface AudioPlayerProps {
  audioUrl?: string;
  filename: string;
  durationSeconds: number;
  suspiciousSections: SuspiciousSection[];
  activeSectionId: string | null;
  onSeekRequested?: number | null;
  onSelectSection?: (section: SuspiciousSection) => void;
  className?: string;
}

const PLAYBACK_SPEEDS = [0.75, 1, 1.25, 1.5, 2];

export const AudioPlayer: React.FC<AudioPlayerProps> = ({
  audioUrl,
  filename,
  durationSeconds,
  suspiciousSections,
  activeSectionId,
  onSeekRequested,
  onSelectSection,
  className,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.85);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const intervalRef = useRef<number | null>(null);

  const totalDuration = durationSeconds > 0 ? durationSeconds : 18.2;

  // React to external seek requests (e.g. from clicking a suspicious section card)
  useEffect(() => {
    if (onSeekRequested !== null && onSeekRequested !== undefined) {
      handleSeek(onSeekRequested);
    }
  }, [onSeekRequested]);

  // Timer simulation if no real audio source or audio fails to play
  useEffect(() => {
    if (isPlaying) {
      intervalRef.current = window.setInterval(() => {
        setCurrentTime((prev) => {
          if (prev >= totalDuration) {
            setIsPlaying(false);
            return 0;
          }
          return prev + 0.1 * playbackSpeed;
        });
      }, 100);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isPlaying, totalDuration, playbackSpeed]);

  const togglePlay = () => {
    if (audioRef.current && audioUrl) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play().catch(() => {
          // Fallback to simulation mode if browser blocks audio autoplay
        });
      }
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (newTimeSeconds: number) => {
    const clamped = Math.max(0, Math.min(totalDuration, newTimeSeconds));
    setCurrentTime(clamped);
    if (audioRef.current) {
      audioRef.current.currentTime = clamped;
    }
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    if (audioRef.current) {
      audioRef.current.playbackRate = speed;
    }
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (audioRef.current) {
      audioRef.current.volume = val;
    }
    if (val === 0) setIsMuted(true);
    else setIsMuted(false);
  };

  return (
    <div
      className={cn(
        'rounded-lg border border-border-subtle bg-bg-surface p-5 space-y-4 shadow-sm',
        className
      )}
      aria-label="Investigation Audio Player"
    >
      {/* Hidden native audio element */}
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onTimeUpdate={() => {
            if (audioRef.current) {
              setCurrentTime(audioRef.current.currentTime);
            }
          }}
          onEnded={() => setIsPlaying(false)}
        />
      )}

      {/* Top Details & File header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-brand animate-pulse" />
          <span className="text-xs font-mono font-semibold text-txt-main">
            {filename}
          </span>
          <span className="text-[11px] font-mono text-txt-dim">
            · {totalDuration.toFixed(1)}s forensic inspection track
          </span>
        </div>

        {suspiciousSections.length > 0 && (
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20 text-xs font-mono text-rose-400">
            <Sparkles className="w-3.5 h-3.5" />
            <span>{suspiciousSections.length} suspicious sections localized</span>
          </div>
        )}
      </div>

      {/* Interactive Waveform / Timeline */}
      <AudioTimeline
        currentTime={currentTime}
        duration={totalDuration}
        suspiciousSections={suspiciousSections}
        activeSectionId={activeSectionId}
        onSeek={handleSeek}
        onSelectSection={onSelectSection}
      />

      {/* Playback Controls & Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
        {/* Left: Play/Pause, Rewind */}
        <div className="flex items-center gap-3">
          <button
            onClick={togglePlay}
            className="w-10 h-10 rounded-full bg-brand hover:bg-brand-hover text-white flex items-center justify-center shadow-subtle transition-all active:scale-95"
            aria-label={isPlaying ? 'Pause playback' : 'Start playback'}
          >
            {isPlaying ? <Pause className="w-5 h-5 fill-white" /> : <Play className="w-5 h-5 fill-white ml-0.5" />}
          </button>

          <button
            onClick={() => handleSeek(0)}
            className="p-2 rounded-md hover:bg-bg-surface-hover text-txt-muted hover:text-txt-main transition-colors"
            title="Restart to beginning (00:00)"
            aria-label="Restart audio"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Speed Buttons: 0.75x / 1x / 1.25x / 1.5x / 2x */}
          <div className="flex items-center gap-1 border border-border-subtle rounded-md p-0.5 bg-bg-surface-elevated">
            {PLAYBACK_SPEEDS.map((speed) => (
              <button
                key={speed}
                onClick={() => handleSpeedChange(speed)}
                className={cn(
                  'px-2 py-1 text-xs font-mono rounded transition-colors',
                  playbackSpeed === speed
                    ? 'bg-brand text-white font-bold'
                    : 'text-txt-muted hover:text-txt-main hover:bg-bg-surface-hover'
                )}
                aria-label={`Playback speed ${speed}x`}
              >
                {speed}x
              </button>
            ))}
          </div>
        </div>

        {/* Right: Volume slider */}
        <div className="flex items-center gap-2">
          <button
            onClick={toggleMute}
            className="p-1.5 rounded text-txt-muted hover:text-txt-main transition-colors"
            aria-label={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted || volume === 0 ? (
              <VolumeX className="w-4 h-4 text-rose-400" />
            ) : (
              <Volume2 className="w-4 h-4" />
            )}
          </button>

          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={isMuted ? 0 : volume}
            onChange={handleVolumeChange}
            className="w-20 h-1.5 bg-bg-surface-elevated rounded-lg appearance-none cursor-pointer accent-brand"
            aria-label="Volume slider"
          />
        </div>
      </div>
    </div>
  );
};
