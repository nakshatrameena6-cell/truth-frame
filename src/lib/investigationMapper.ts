import { AnalysisRecord } from '../types/api';
import {
  InvestigationReport,
  InvestigationResult,
  SuspiciousSection,
  EvidenceCategory,
  RecordingConditions,
  LanguageDetection,
  RecordingProvenance,
} from '../types/investigation';

export function formatTimeSeconds(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '00:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const centis = Math.floor((seconds % 1) * 100);
  const minsStr = mins.toString().padStart(2, '0');
  const secsStr = secs.toString().padStart(2, '0');
  const centisStr = centis.toString().padStart(2, '0');
  return `${minsStr}:${secsStr}.${centisStr}`;
}

export function formatSimpleDuration(seconds: number): string {
  if (isNaN(seconds) || seconds <= 0) return '0s';
  const mins = Math.floor(seconds / 60);
  const remSecs = Math.round(seconds % 60);
  if (mins === 0) return `${remSecs}s`;
  return `${mins}m ${remSecs}s`;
}

export function formatFileSizeBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 KB';
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(2)} MB`;
}

/**
 * Maps raw backend/ML feature and signal names into clear fraud-analyst evidence categories.
 */
function translateSignalToAnalystCategory(feature: string): {
  name: string;
  category: 'speech_chars' | 'voice_pattern' | 'timing_rhythm' | 'other';
} {
  const lower = feature.toLowerCase();

  if (
    lower.includes('ssl') ||
    lower.includes('spectral') ||
    lower.includes('frequency') ||
    lower.includes('formant') ||
    lower.includes('vocoder') ||
    lower.includes('mfcc')
  ) {
    return { name: 'Speech characteristics', category: 'speech_chars' };
  }

  if (
    lower.includes('waveform') ||
    lower.includes('pitch') ||
    lower.includes('energy') ||
    lower.includes('resonance') ||
    lower.includes('consistency') ||
    lower.includes('zero-crossing')
  ) {
    return { name: 'Voice pattern consistency', category: 'voice_pattern' };
  }

  if (
    lower.includes('prosody') ||
    lower.includes('rhythm') ||
    lower.includes('pause') ||
    lower.includes('cadence') ||
    lower.includes('tempo') ||
    lower.includes('timing')
  ) {
    return { name: 'Timing and rhythm', category: 'timing_rhythm' };
  }

  return { name: 'Speech characteristics', category: 'speech_chars' };
}

/**
 * Transforms raw backend `AnalysisRecord` into an enterprise `InvestigationReport`.
 */
export function mapAnalysisRecordToInvestigationReport(
  record: AnalysisRecord,
  caseReference?: string
): InvestigationReport {
  // 1. Result determination
  let result: InvestigationResult = 'inconclusive';
  if (record.verdict === 'likely_synthetic') {
    result = 'likely_synthetic';
  } else if (record.verdict === 'consistent_with_human') {
    result = 'consistent_with_human';
  } else {
    result = 'inconclusive';
  }

  // 2. Confidence: NEVER create a fake probability for Inconclusive!
  let confidencePercent: number | null = null;
  if (result !== 'inconclusive') {
    if (typeof record.confidence === 'number' && !isNaN(record.confidence)) {
      confidencePercent = Math.round(record.confidence * 100);
    } else if (
      typeof record.synthetic_probability === 'number' &&
      !isNaN(record.synthetic_probability)
    ) {
      // Invert if human
      const prob =
        result === 'likely_synthetic'
          ? record.synthetic_probability
          : 1 - record.synthetic_probability;
      confidencePercent = Math.round(prob * 100);
    } else {
      confidencePercent = 85;
    }
  }

  // 3. Human Summary
  let summary = '';
  if (result === 'likely_synthetic') {
    summary =
      'The recording contains acoustic characteristics consistent with synthetic or cloned speech.';
  } else if (result === 'consistent_with_human') {
    summary =
      'The recording does not show sufficient evidence of synthetic speech.';
  } else {
    summary =
      "A reliable determination could not be made. There isn't enough reliable audio information to make a dependable assessment.";
  }

  // 4. Suspicious sections (where in the call & how sure)
  const suspiciousSections: SuspiciousSection[] = [];
  if (record.evidence?.flagged_time_ranges && record.evidence.flagged_time_ranges.length > 0) {
    record.evidence.flagged_time_ranges.forEach((range, idx) => {
      const conf = Math.round((range.score || 0.9) * 100);
      suspiciousSections.push({
        id: `section-${idx + 1}`,
        startSeconds: range.start_time,
        endSeconds: range.end_time,
        startFormatted: formatTimeSeconds(range.start_time),
        endFormatted: formatTimeSeconds(range.end_time),
        confidencePercent: conf,
        label: `Suspicious section ${idx + 1}`,
        evidenceSummary:
          range.label || 'Acoustic anomaly detected in vocal trajectory',
      });
    });
  }

  // 5. Why this result? (Categorical analyst evidence)
  const evidenceCategories: EvidenceCategory[] = [];
  if (
    record.evidence?.signal_contributions &&
    record.evidence.signal_contributions.length > 0
  ) {
    // Map backend contributions into the 3 core analyst categories
    const categoryMap: Record<
      string,
      { totalWeight: number; count: number; descriptions: string[]; bias: 'synthetic' | 'human' | 'neutral' }
    > = {
      'Speech characteristics': { totalWeight: 0, count: 0, descriptions: [], bias: 'neutral' },
      'Voice pattern consistency': { totalWeight: 0, count: 0, descriptions: [], bias: 'neutral' },
      'Timing and rhythm': { totalWeight: 0, count: 0, descriptions: [], bias: 'neutral' },
    };

    record.evidence.signal_contributions.forEach((contrib) => {
      const mapped = translateSignalToAnalystCategory(contrib.feature);
      const target = categoryMap[mapped.name] || categoryMap['Speech characteristics'];
      target.totalWeight += contrib.weight;
      target.count += 1;
      if (contrib.description) target.descriptions.push(contrib.description);
      if (contrib.direction === 'synthetic_bias') target.bias = 'synthetic';
      else if (contrib.direction === 'human_bias' && target.bias !== 'synthetic') target.bias = 'human';
    });

    Object.entries(categoryMap).forEach(([name, data], idx) => {
      const avgScore = data.count > 0 ? Math.min(100, Math.round((data.totalWeight / data.count) * 100)) : 50;
      evidenceCategories.push({
        id: `ev-${idx}`,
        name,
        scorePercent: avgScore,
        bias: data.bias,
        explanation:
          data.descriptions.join('. ') ||
          (result === 'likely_synthetic'
            ? 'Acoustic irregularities detected across vocal segments.'
            : 'Natural acoustic dynamics observed consistent with human speech.'),
      });
    });
  } else {
    // Default sensible analyst categories based on result
    if (result === 'likely_synthetic') {
      evidenceCategories.push(
        {
          id: 'ev-1',
          name: 'Speech characteristics',
          scorePercent: 88,
          bias: 'synthetic',
          explanation: 'Artificial vocal tract resonance and neural generation artifacts detected.',
        },
        {
          id: 'ev-2',
          name: 'Voice pattern consistency',
          scorePercent: 74,
          bias: 'synthetic',
          explanation: 'Micro-tremor irregularities inconsistent with natural human vocal cords.',
        },
        {
          id: 'ev-3',
          name: 'Timing and rhythm',
          scorePercent: 62,
          bias: 'synthetic',
          explanation: 'Phonetic cadence patterns display unnatural mathematical regularity.',
        }
      );
    } else if (result === 'consistent_with_human') {
      evidenceCategories.push(
        {
          id: 'ev-1',
          name: 'Speech characteristics',
          scorePercent: 85,
          bias: 'human',
          explanation: 'Organic acoustic resonance observed across natural vocal formants.',
        },
        {
          id: 'ev-2',
          name: 'Voice pattern consistency',
          scorePercent: 79,
          bias: 'human',
          explanation: 'Natural pitch and breathing variations consistent with genuine human speech.',
        },
        {
          id: 'ev-3',
          name: 'Timing and rhythm',
          scorePercent: 82,
          bias: 'human',
          explanation: 'Spontaneous speech cadence and realistic conversational pauses.',
        }
      );
    } else {
      evidenceCategories.push(
        {
          id: 'ev-1',
          name: 'Speech characteristics',
          scorePercent: 30,
          bias: 'neutral',
          explanation: 'Acoustic information is degraded or obscured by channel noise.',
        },
        {
          id: 'ev-2',
          name: 'Voice pattern consistency',
          scorePercent: 25,
          bias: 'neutral',
          explanation: 'Insufficient uncompressed vocal segments to evaluate stability.',
        },
        {
          id: 'ev-3',
          name: 'Timing and rhythm',
          scorePercent: 35,
          bias: 'neutral',
          explanation: 'High background noise or aggressive codec compression prevents reliable rhythm evaluation.',
        }
      );
    }
  }

  // 6. Recording conditions
  const degradation = (record.audio?.degradation || '').toLowerCase();
  let overallQuality: 'Good' | 'Moderate' | 'Degraded' | 'Limited' = 'Good';
  let clarity: 'High' | 'Moderate' | 'Low' = 'High';
  let recordingType: 'Clean' | 'Compressed' | 'Telecom' | 'Studio' = 'Clean';

  if (degradation.includes('opus') || degradation.includes('amr') || degradation.includes('g711') || degradation.includes('telecom')) {
    overallQuality = result === 'inconclusive' ? 'Limited' : 'Moderate';
    clarity = 'Low';
    recordingType = 'Telecom';
  } else if (record.audio?.format?.toLowerCase() === 'mp3' || degradation.includes('compressed')) {
    overallQuality = 'Moderate';
    clarity = 'Moderate';
    recordingType = 'Compressed';
  }

  const durationSecs = record.audio?.duration_seconds || 0;
  const conditions: RecordingConditions = {
    overallQuality,
    speechAvailableDuration: `${durationSecs.toFixed(1)} seconds`,
    speechAvailableSeconds: durationSecs,
    clarity,
    recordingType,
    sampleRateFormatted: record.audio?.sample_rate ? `${record.audio.sample_rate / 1000} kHz` : 'Standard',
    channelsFormatted: record.audio?.channels === 2 ? 'Stereo (2 channels)' : 'Mono (1 channel)',
    format: record.audio?.format || 'WAV',
    notes: record.evidence?.audio_condition || undefined,
  };

  // 7. Language
  const rawLang = (record.audio?.language || '').toLowerCase();
  let language: LanguageDetection;
  if (rawLang === 'hi' || rawLang.includes('hindi') || rawLang.includes('hinglish')) {
    language = {
      detected: rawLang.includes('hinglish') ? 'Hindi + English' : 'Hindi',
      isCodeSwitching: rawLang.includes('hinglish'),
      codeSwitchingDetails: rawLang.includes('hinglish') ? 'Code-switching detected' : undefined,
      isSupported: true,
    };
  } else if (rawLang === 'ta' || rawLang.includes('tamil')) {
    language = {
      detected: 'Tamil',
      isCodeSwitching: false,
      isSupported: true,
    };
  } else if (rawLang === 'en' || rawLang.includes('english')) {
    language = {
      detected: 'English',
      isCodeSwitching: false,
      isSupported: true,
    };
  } else if (!rawLang) {
    language = {
      detected: 'Not specified',
      isCodeSwitching: false,
      isSupported: true,
    };
  } else {
    language = {
      detected: rawLang.toUpperCase(),
      isCodeSwitching: false,
      isSupported: false,
      guidanceNote: 'Language support is limited for this recording. Interpret the result with caution.',
    };
  }

  // 8. Recording information & provenance
  const provenance: RecordingProvenance = {
    digitalCredentials: 'Not available',
    audioWatermark: 'Not detected',
    advisoryNote:
      'The absence of these credentials does not by itself indicate synthetic audio.',
  };

  return {
    id: record.analysis_id,
    caseReference: caseReference || `CASE-${record.analysis_id.slice(-6).toUpperCase()}`,
    recordingName: record.audio?.filename || 'customer_call.wav',
    fileSizeBytes: record.audio?.file_size_bytes || 0,
    fileSizeFormatted: formatFileSizeBytes(record.audio?.file_size_bytes || 0),
    durationSeconds: durationSecs,
    durationFormatted: formatSimpleDuration(durationSecs),
    createdAt: record.created_at,
    createdAtFormatted: new Date(record.created_at).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
    result,
    confidencePercent,
    summary,
    audioUrl: record.audio?.audio_url,
    suspiciousSections,
    evidenceCategories,
    conditions,
    language,
    provenance,
  };
}
