import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Play, Pause, RefreshCw, Send, AlertCircle } from 'lucide-react';
import { formatDuration } from '../../lib/utils';
import { cn } from '../../lib/utils';

interface AudioRecorderProps {
  onRecorded: (file: File) => void;
  disabled?: boolean;
}

export const AudioRecorder: React.FC<AudioRecorderProps> = ({ onRecorded, disabled = false }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isPlayingPreview, setIsPlayingPreview] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerIntervalRef = useRef<number | null>(null);
  const audioPreviewRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, []);

  const startRecording = async () => {
    setMicError(null);
    setRecordedBlob(null);
    setRecordingTime(0);
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setRecordedBlob(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start(100);
      setIsRecording(true);

      timerIntervalRef.current = window.setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Failed to access microphone', err);
      setMicError('Microphone access denied or unavailable. Please check browser permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    }
  };

  const togglePreview = () => {
    if (!audioPreviewRef.current && recordedBlob) {
      const url = URL.createObjectURL(recordedBlob);
      audioPreviewRef.current = new Audio(url);
      audioPreviewRef.current.onended = () => setIsPlayingPreview(false);
    }

    if (audioPreviewRef.current) {
      if (isPlayingPreview) {
        audioPreviewRef.current.pause();
        setIsPlayingPreview(false);
      } else {
        audioPreviewRef.current.play();
        setIsPlayingPreview(true);
      }
    }
  };

  const resetRecording = () => {
    if (audioPreviewRef.current) {
      audioPreviewRef.current.pause();
      audioPreviewRef.current = null;
    }
    setRecordedBlob(null);
    setRecordingTime(0);
    setIsPlayingPreview(false);
    setMicError(null);
  };

  const submitRecording = () => {
    if (!recordedBlob) return;
    const filename = `recorded_speech_${Date.now()}.wav`;
    const file = new File([recordedBlob], filename, { type: 'audio/wav' });
    onRecorded(file);
  };

  return (
    <div className="rounded-lg border border-border-strong bg-bg-surface p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-bg-surface-elevated border border-border-subtle flex items-center justify-center text-brand">
            <Mic className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-txt-main">Direct Audio Capture</h4>
            <p className="text-[11px] text-txt-muted font-mono">Record live speech directly from browser input</p>
          </div>
        </div>

        {/* Timer readout */}
        <div className="font-mono text-sm font-semibold text-txt-main px-3 py-1 rounded bg-bg-surface-elevated border border-border-subtle">
          {formatDuration(recordingTime)}
        </div>
      </div>

      {micError && (
        <div className="flex items-center gap-2 p-3 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-mono">
          <AlertCircle className="w-4 h-4 text-rose-500" />
          <span>{micError}</span>
        </div>
      )}

      {/* Recording Control Action Row */}
      <div className="flex items-center justify-center gap-3 py-2">
        {!isRecording && !recordedBlob && (
          <button
            onClick={startRecording}
            disabled={disabled}
            className="flex items-center gap-2 px-5 py-2.5 rounded-md bg-rose-600 hover:bg-rose-700 text-white font-mono text-xs font-semibold shadow-subtle transition-colors disabled:opacity-50"
          >
            <Mic className="w-4 h-4 animate-pulse" />
            <span>Start Microphone Capture</span>
          </button>
        )}

        {isRecording && (
          <button
            onClick={stopRecording}
            className="flex items-center gap-2 px-5 py-2.5 rounded-md bg-rose-600 hover:bg-rose-700 text-white font-mono text-xs font-semibold shadow-subtle transition-colors"
          >
            <Square className="w-4 h-4" />
            <span>Stop Recording ({formatDuration(recordingTime)})</span>
          </button>
        )}

        {recordedBlob && (
          <div className="flex items-center gap-2">
            <button
              onClick={togglePreview}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-bg-surface-elevated border border-border-subtle text-txt-main text-xs font-mono font-medium hover:bg-bg-surface-hover transition-colors"
            >
              {isPlayingPreview ? <Pause className="w-3.5 h-3.5 text-brand" /> : <Play className="w-3.5 h-3.5 text-brand" />}
              <span>{isPlayingPreview ? 'Pause Preview' : 'Play Preview'}</span>
            </button>

            <button
              onClick={resetRecording}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-bg-surface-elevated border border-border-subtle text-txt-muted text-xs font-mono hover:text-txt-main hover:bg-bg-surface-hover transition-colors"
              title="Discard and re-record"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Discard</span>
            </button>

            <button
              onClick={submitRecording}
              disabled={disabled}
              className="flex items-center gap-2 px-4 py-1.5 rounded bg-brand hover:bg-brand-hover text-white font-mono text-xs font-semibold shadow-subtle transition-colors disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Submit for Analysis</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
