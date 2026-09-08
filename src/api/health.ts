import { HealthResponse } from '../types/api';
import { fetchApi, isMockModeEnabled } from './client';
import { INITIAL_MOCK_HEALTH } from './mockData';

export async function getHealth(): Promise<HealthResponse> {
  if (isMockModeEnabled()) {
    return {
      ...INITIAL_MOCK_HEALTH,
      timestamp: new Date().toISOString(),
    };
  }
  return fetchApi<HealthResponse>('/health');
}
