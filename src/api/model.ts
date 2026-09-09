import { ModelInfo } from '../types/api';
import { fetchApi, isMockModeEnabled } from './client';
import { INITIAL_MOCK_MODEL } from './mockData';

export async function getModelInfo(): Promise<ModelInfo> {
  if (isMockModeEnabled()) {
    return INITIAL_MOCK_MODEL;
  }
  return fetchApi<ModelInfo>('/api/v1/model');
}
