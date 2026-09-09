import { MOCK_ANALYSES_SEED, INITIAL_MOCK_MODEL, INITIAL_MOCK_FORMATS, INITIAL_MOCK_HEALTH } from './mockData';
import {
  AnalysisRecord,
  CreateAnalysisParams,
  HealthResponse,
  ModelInfo,
  AudioFormatsResponse,
  ApiErrorResponse,
  Verdict,
} from '../types/api';

const STORAGE_KEY_USE_MOCK = 'pandamind_use_mock';
const STORAGE_KEY_ANALYSES = 'pandamind_analyses_db';

export function isMockModeEnabled(): boolean {
  const val = localStorage.getItem(STORAGE_KEY_USE_MOCK);
  // Default to mock mode if not explicitly set to 'false'
  return val === null ? true : val === 'true';
}

export function setMockModeEnabled(enabled: boolean): void {
  localStorage.setItem(STORAGE_KEY_USE_MOCK, String(enabled));
}

export function getStoredAnalyses(): AnalysisRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_ANALYSES);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY_ANALYSES, JSON.stringify(MOCK_ANALYSES_SEED));
      return MOCK_ANALYSES_SEED;
    }
    return JSON.parse(raw);
  } catch {
    return MOCK_ANALYSES_SEED;
  }
}

export function saveStoredAnalyses(records: AnalysisRecord[]): void {
  try {
    localStorage.setItem(STORAGE_KEY_ANALYSES, JSON.stringify(records));
  } catch (err) {
    console.error('Failed to persist mock analysis store to localStorage', err);
  }
}

export function resetMockDataToDefault(): void {
  localStorage.setItem(STORAGE_KEY_ANALYSES, JSON.stringify(MOCK_ANALYSES_SEED));
}

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(endpoint, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorData: ApiErrorResponse;
    try {
      errorData = await response.json();
    } catch {
      errorData = {
        error_code: 'INTERNAL_ERROR',
        message: `HTTP error ${response.status}: ${response.statusText}`,
      };
    }
    throw errorData;
  }

  return response.json();
}
