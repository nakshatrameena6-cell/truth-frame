import {
  AnalysisRecord,
  CreateAnalysisParams,
  Verdict,
  ApiErrorResponse,
} from '../types/api';
import {
  fetchApi,
  isMockModeEnabled,
  getStoredAnalyses,
  saveStoredAnalyses,
} from './client';

export async function createAnalysis(params: CreateAnalysisParams): Promise<AnalysisRecord> {
  if (isMockModeEnabled()) {
    // Validate size
    if (params.audio.size > 26214400) {
      const err: ApiErrorResponse = {
        error_code: 'FILE_TOO_LARGE',
        message: 'The audio file exceeds the maximum allowed upload size (25 MB).',
      };
      throw err;
    }

    const filename = params.filename || (params.audio as File).name || 'recorded_speech.wav';
    const ext = filename.split('.').pop()?.toLowerCase() || 'wav';
    const allowed = ['wav', 'mp3', 'flac', 'ogg', 'm4a'];
    if (!allowed.includes(ext)) {
      const err: ApiErrorResponse = {
        error_code: 'UNSUPPORTED_AUDIO',
        message: 'The submitted audio format is unsupported. Please submit a WAV, MP3, FLAC, OGG, or M4A file.',
      };
      throw err;
    }

    const audioUrl = URL.createObjectURL(params.audio);
    const id = `ana_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 6)}`;
    const now = new Date().toISOString();

    const record: AnalysisRecord = {
      analysis_id: id,
      created_at: now,
      updated_at: now,
      status: 'queued',
      verdict: null,
      synthetic_probability: null,
      confidence: null,
      error_code: null,
      error_message: null,
      audio: {
        filename,
        file_size_bytes: params.audio.size,
        duration_seconds: 14.5, // Estimated/detected
        sample_rate: 16000,
        channels: 1,
        format: ext.toUpperCase(),
        language: params.language || 'en',
        degradation: 'clean',
        source: params.source || 'user_upload',
        audio_url: audioUrl,
      },
      model: {
        name: 'PandaMIND Detector',
        version: 'phase9-experimental',
      },
      evidence: null,
    };

    const current = getStoredAnalyses();
    const updated = [record, ...current];
    saveStoredAnalyses(updated);

    // Asynchronously advance status through queued -> processing -> completed
    setTimeout(() => {
      const db = getStoredAnalyses();
      const target = db.find((a) => a.analysis_id === id);
      if (target && target.status === 'queued') {
        target.status = 'processing';
        target.updated_at = new Date().toISOString();
        saveStoredAnalyses(db);
      }
    }, 1500);

    setTimeout(() => {
      const db = getStoredAnalyses();
      const target = db.find((a) => a.analysis_id === id);
      if (target && target.status === 'processing') {
        // Randomly produce representative verdict for demo
        const rand = Math.random();
        let verdict: Verdict;
        let prob: number;
        let conf: number;

        if (rand < 0.4) {
          verdict = 'likely_synthetic';
          prob = 0.91 + Math.random() * 0.07;
          conf = 0.88;
        } else if (rand < 0.7) {
          verdict = 'consistent_with_human';
          prob = 0.11 + Math.random() * 0.12;
          conf = 0.93;
        } else {
          verdict = 'inconclusive';
          prob = 0.748;
          conf = 0.65;
        }

        target.status = 'completed';
        target.updated_at = new Date().toISOString();
        target.verdict = verdict;
        target.synthetic_probability = Number(prob.toFixed(3));
        target.confidence = Number(conf.toFixed(2));
        target.evidence = {
          signal_contributions: [
            {
              feature: 'Spectral Centroid Shift',
              weight: 0.45,
              description: 'Acoustic spectral distribution signature',
              direction: verdict === 'likely_synthetic' ? 'synthetic_bias' : verdict === 'consistent_with_human' ? 'human_bias' : 'neutral',
            },
            {
              feature: 'Zero-Crossing Rate Modulation',
              weight: 0.35,
              description: 'High frequency acoustic frame noise variance',
              direction: verdict === 'likely_synthetic' ? 'synthetic_bias' : verdict === 'consistent_with_human' ? 'human_bias' : 'neutral',
            },
            {
              feature: 'Frame Energy Modulation',
              weight: 0.20,
              description: 'Temporal acoustic envelope modulation dynamics',
              direction: 'neutral',
            },
          ],
          audio_condition: 'Analyzed (Normalized Peak Amplitude)',
          language_match: `${params.language || 'en'} — Matched`,
          provenance: verdict === 'likely_synthetic' ? 'Neural Vocoder Synthesis' : verdict === 'consistent_with_human' ? 'Authentic Human Acoustic Capture' : 'Ambiguous acoustic score',
          model_name: 'PandaMIND Detector',
          model_version: 'phase9-experimental',
          low_threshold: 0.7408,
          high_threshold: 0.7556,
          flagged_time_ranges: verdict === 'likely_synthetic' ? [
            { start_time: 1.2, end_time: 4.5, label: 'High vocoder probability segment', score: 0.93 }
          ] : [],
          raw_score: verdict === 'likely_synthetic' ? 2.84 : -1.92,
          ece_score: 0.045,
        };
        saveStoredAnalyses(db);
      }
    }, 4000);

    return record;
  }

  // Live REST API mode
  const formData = new FormData();
  formData.append('audio', params.audio, params.filename);
  if (params.language) formData.append('language', params.language);
  if (params.source) formData.append('source', params.source);

  return fetchApi<AnalysisRecord>('/api/v1/analyses', {
    method: 'POST',
    body: formData,
  });
}

export async function getAnalysis(analysisId: string): Promise<AnalysisRecord> {
  if (isMockModeEnabled()) {
    const list = getStoredAnalyses();
    const found = list.find((a) => a.analysis_id === analysisId);
    if (!found) {
      const err: ApiErrorResponse = {
        error_code: 'ANALYSIS_NOT_FOUND',
        message: `Analysis record '${analysisId}' was not found.`,
      };
      throw err;
    }
    return found;
  }

  return fetchApi<AnalysisRecord>(`/api/v1/analyses/${analysisId}`);
}

export async function listAnalyses(): Promise<AnalysisRecord[]> {
  if (isMockModeEnabled()) {
    return getStoredAnalyses();
  }

  return fetchApi<AnalysisRecord[]>('/api/v1/analyses');
}

export async function deleteAnalysis(analysisId: string): Promise<{ success: boolean; analysis_id: string }> {
  if (isMockModeEnabled()) {
    const list = getStoredAnalyses();
    const filtered = list.filter((a) => a.analysis_id !== analysisId);
    saveStoredAnalyses(filtered);
    return { success: true, analysis_id: analysisId };
  }

  return fetchApi<{ success: boolean; analysis_id: string }>(`/api/v1/analyses/${analysisId}`, {
    method: 'DELETE',
  });
}
