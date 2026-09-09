import { AudioFormatsResponse } from '../types/api';
import { fetchApi, isMockModeEnabled } from './client';
import { INITIAL_MOCK_FORMATS } from './mockData';

export async function getAudioFormats(): Promise<AudioFormatsResponse> {
  if (isMockModeEnabled()) {
    return INITIAL_MOCK_FORMATS;
  }
  return fetchApi<AudioFormatsResponse>('/api/v1/audio/formats');
}
