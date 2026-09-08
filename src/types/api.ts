export type Verdict = 'consistent_with_human' | 'inconclusive' | 'likely_synthetic';

export type AnalysisStatus = 'queued' | 'processing' | 'completed' | 'failed';

export type ApiErrorCode =
  | 'INVALID_REQUEST'
  | 'UNSUPPORTED_AUDIO'
  | 'FILE_TOO_LARGE'
  | 'AUDIO_TOO_LONG'
  | 'AUDIO_DECODE_FAILED'
  | 'ANALYSIS_NOT_FOUND'
  | 'ANALYSIS_FAILED'
  | 'MODEL_UNAVAILABLE'
  | 'RATE_LIMITED'
  | 'INTERNAL_ERROR';

export interface ApiErrorResponse {
  error_code: ApiErrorCode;
  message: string;
  details?: Record<string, unknown>;
}

export interface OperatingPoints {
  fpr_0_1: number;
  fpr_1: number;
  fpr_5: number;
}

export interface Thresholds {
  low: number;
  high: number;
}

export interface ModelInfo {
  name: string;
  version: string;
  status: string;
  calibration_status: string;
  temperature: number;
  operating_points: OperatingPoints;
  thresholds: Thresholds;
  supported_languages: string[];
}

export interface AudioMetadata {
  filename: string;
  file_size_bytes: number;
  duration_seconds: number;
  sample_rate: number;
  channels: number;
  format: string;
  language: string | null;
  degradation: string | null;
  source: string | null;
  audio_url?: string;
}

export interface SignalContribution {
  feature: string;
  weight: number;
  description: string;
  direction: 'synthetic_bias' | 'human_bias' | 'neutral';
}

export interface FlaggedTimeRange {
  start_time: number;
  end_time: number;
  label: string;
  score: number;
}

export interface EvidencePayload {
  signal_contributions: SignalContribution[];
  audio_condition: string;
  language_match: string;
  provenance: string;
  model_name: string;
  model_version: string;
  low_threshold: number;
  high_threshold: number;
  flagged_time_ranges: FlaggedTimeRange[];
  raw_score?: number;
  ece_score?: number;
}

export interface AnalysisRecord {
  analysis_id: string;
  created_at: string;
  updated_at: string;
  status: AnalysisStatus;
  verdict: Verdict | null;
  synthetic_probability: number | null;
  confidence: number | null;
  error_code: ApiErrorCode | null;
  error_message: string | null;
  audio: AudioMetadata;
  model: {
    name: string;
    version: string;
  };
  evidence: EvidencePayload | null;
}

export interface AudioFormatsResponse {
  supported_extensions: string[];
  max_file_size_bytes: number;
  max_duration_seconds: number;
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error';
  version: string;
  model_loaded: boolean;
  model_version: string;
  timestamp: string;
}

export interface CreateAnalysisParams {
  audio: File | Blob;
  filename?: string;
  language?: string;
  source?: string;
}
