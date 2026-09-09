import { ApiErrorCode } from '../types/api';

const ERROR_MESSAGES: Record<ApiErrorCode, string> = {
  INVALID_REQUEST: 'The submission request was invalid or missing required parameters.',
  UNSUPPORTED_AUDIO: 'The submitted audio format is unsupported. Please submit a WAV, MP3, FLAC, OGG, or M4A file.',
  FILE_TOO_LARGE: 'The audio file exceeds the maximum allowed upload size (25 MB).',
  AUDIO_TOO_LONG: 'The audio recording duration exceeds the maximum limit (5 minutes).',
  AUDIO_DECODE_FAILED: 'Failed to decode the audio stream. The file may be corrupted or in an unreadable format.',
  ANALYSIS_NOT_FOUND: 'The requested audio analysis record could not be found.',
  ANALYSIS_FAILED: 'The acoustic detector encountered an unrecoverable error during inference.',
  MODEL_UNAVAILABLE: 'The PandaMIND detection model is currently offline or re-calibrating.',
  RATE_LIMITED: 'Too many analysis requests submitted within a short window. Please wait a moment and retry.',
  INTERNAL_ERROR: 'An internal server error occurred while processing the audio analysis.',
};

export function getHumanReadableErrorMessage(errorCode: ApiErrorCode | string | null | undefined, fallbackMessage?: string | null): string {
  if (errorCode && errorCode in ERROR_MESSAGES) {
    return ERROR_MESSAGES[errorCode as ApiErrorCode];
  }
  return fallbackMessage || 'An unexpected error occurred during audio analysis. Please try again.';
}
