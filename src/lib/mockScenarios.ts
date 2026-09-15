import { InvestigationReport, ScenarioId } from '../types/investigation';

export const MOCK_SCENARIOS: Record<ScenarioId, InvestigationReport> = {
  'scenario-a': {
    id: 'case-syn-0491',
    caseReference: 'CASE-2026-8821',
    recordingName: 'inbound_verification_call_hi_en.wav',
    fileSizeBytes: 3942100,
    fileSizeFormatted: '3.76 MB',
    durationSeconds: 18.2,
    durationFormatted: '18s',
    createdAt: new Date(Date.now() - 3600000 * 2).toISOString(),
    createdAtFormatted: 'Today at 08:30 AM',
    result: 'likely_synthetic',
    confidencePercent: 87,
    summary:
      'The recording contains acoustic characteristics consistent with synthetic or cloned speech.',
    suspiciousSections: [
      {
        id: 'sec-1',
        startSeconds: 4.12,
        endSeconds: 6.89,
        startFormatted: '00:04.12',
        endFormatted: '00:06.89',
        confidencePercent: 94,
        label: 'Synthetic voice synthesis artifact',
        evidenceSummary:
          'Phase continuity distortion and spectral discontinuity across high-frequency vocal formants.',
      },
      {
        id: 'sec-2',
        startSeconds: 11.04,
        endSeconds: 12.30,
        startFormatted: '00:11.04',
        endFormatted: '00:12.30',
        confidencePercent: 89,
        label: 'Cloned prosody regularity',
        evidenceSummary:
          'Unnatural micro-tremor absence and flat noise floor between phonetic transitions.',
      },
    ],
    evidenceCategories: [
      {
        id: 'ev-1',
        name: 'Speech characteristics',
        scorePercent: 89,
        bias: 'synthetic',
        explanation:
          'Synthetic vocoder artifacts detected in upper harmonic bands consistent with neural voice cloning.',
      },
      {
        id: 'ev-2',
        name: 'Voice pattern consistency',
        scorePercent: 78,
        bias: 'synthetic',
        explanation:
          'Acoustic resonance patterns deviate from biological vocal tract behavior during consonant transitions.',
      },
      {
        id: 'ev-3',
        name: 'Timing and rhythm',
        scorePercent: 64,
        bias: 'synthetic',
        explanation:
          'Speech cadence and pause intervals display mathematical regularity common in automated speech generators.',
      },
    ],
    conditions: {
      overallQuality: 'Good',
      speechAvailableDuration: '18.2 seconds',
      speechAvailableSeconds: 18.2,
      clarity: 'High',
      recordingType: 'Clean',
      sampleRateFormatted: '24.0 kHz',
      channelsFormatted: 'Mono (1 channel)',
      format: 'WAV',
      notes: 'Clean acoustic capture with high signal-to-noise ratio.',
    },
    language: {
      detected: 'Hindi + English',
      isCodeSwitching: true,
      codeSwitchingDetails: 'Code-switching detected',
      isSupported: true,
    },
    provenance: {
      digitalCredentials: 'Not available',
      audioWatermark: 'Not detected',
      advisoryNote:
        'The absence of these credentials does not by itself indicate synthetic audio.',
    },
  },

  'scenario-b': {
    id: 'case-hum-1042',
    caseReference: 'CASE-2026-7734',
    recordingName: 'customer_support_tamil_query.wav',
    fileSizeBytes: 4821040,
    fileSizeFormatted: '4.60 MB',
    durationSeconds: 24.5,
    durationFormatted: '24s',
    createdAt: new Date(Date.now() - 3600000 * 5).toISOString(),
    createdAtFormatted: 'Today at 05:15 AM',
    result: 'consistent_with_human',
    confidencePercent: 92,
    summary:
      'The recording does not show sufficient evidence of synthetic speech.',
    suspiciousSections: [],
    evidenceCategories: [
      {
        id: 'ev-1',
        name: 'Speech characteristics',
        scorePercent: 91,
        bias: 'human',
        explanation:
          'Organic spectral dispersion and natural biological resonance observed across vocal formants.',
      },
      {
        id: 'ev-2',
        name: 'Voice pattern consistency',
        scorePercent: 86,
        bias: 'human',
        explanation:
          'Genuine vocal cord micro-tremors and natural breath inhalation pauses present throughout the recording.',
      },
      {
        id: 'ev-3',
        name: 'Timing and rhythm',
        scorePercent: 88,
        bias: 'human',
        explanation:
          'Spontaneous conversational cadence with natural syllable elongation and authentic pauses.',
      },
    ],
    conditions: {
      overallQuality: 'Good',
      speechAvailableDuration: '24.5 seconds',
      speechAvailableSeconds: 24.5,
      clarity: 'High',
      recordingType: 'Clean',
      sampleRateFormatted: '16.0 kHz',
      channelsFormatted: 'Mono (1 channel)',
      format: 'WAV',
      notes: 'Clean studio/direct microphone capture without heavy compression.',
    },
    language: {
      detected: 'Tamil',
      isCodeSwitching: false,
      isSupported: true,
    },
    provenance: {
      digitalCredentials: 'Not available',
      audioWatermark: 'Not detected',
      advisoryNote:
        'The absence of these credentials does not by itself indicate synthetic audio.',
    },
  },

  'scenario-c': {
    id: 'case-inc-2918',
    caseReference: 'CASE-2026-6219',
    recordingName: 'voicemail_telecom_opus.opus',
    fileSizeBytes: 842100,
    fileSizeFormatted: '822.4 KB',
    durationSeconds: 9.4,
    durationFormatted: '9s',
    createdAt: new Date(Date.now() - 3600000 * 18).toISOString(),
    createdAtFormatted: 'Yesterday at 04:20 PM',
    result: 'inconclusive',
    confidencePercent: null, // PRD RULE: NEVER create a fake probability for Inconclusive!
    summary:
      "A reliable determination could not be made. There isn't enough reliable audio information to make a dependable assessment.",
    suspiciousSections: [],
    evidenceCategories: [
      {
        id: 'ev-1',
        name: 'Speech characteristics',
        scorePercent: 32,
        bias: 'neutral',
        explanation:
          'Aggressive telecom codec bandwidth reduction (8 kHz) stripped spectral harmonics required for reliable assessment.',
      },
      {
        id: 'ev-2',
        name: 'Voice pattern consistency',
        scorePercent: 28,
        bias: 'neutral',
        explanation:
          'High ambient acoustic degradation obscures vocal stability measurements.',
      },
      {
        id: 'ev-3',
        name: 'Timing and rhythm',
        scorePercent: 35,
        bias: 'neutral',
        explanation:
          'Insufficient continuous speech available (< 10 seconds total signal duration).',
      },
    ],
    conditions: {
      overallQuality: 'Limited',
      speechAvailableDuration: '6.2 seconds',
      speechAvailableSeconds: 6.2,
      clarity: 'Low',
      recordingType: 'Telecom',
      sampleRateFormatted: '8.0 kHz',
      channelsFormatted: 'Mono (1 channel)',
      format: 'Opus (AMR/Telecom band)',
      notes:
        'Bandwidth severely restricted below 4 kHz. Excessive packet compression artifacts present.',
    },
    language: {
      detected: 'Hindi',
      isCodeSwitching: false,
      isSupported: true,
    },
    provenance: {
      digitalCredentials: 'Not available',
      audioWatermark: 'Not detected',
      advisoryNote:
        'The absence of these credentials does not by itself indicate synthetic audio.',
    },
  },

  'scenario-d': {
    id: 'case-dif-5510',
    caseReference: 'CASE-2026-4402',
    recordingName: 'noisy_telephony_loan_dispatch.mp3',
    fileSizeBytes: 1820400,
    fileSizeFormatted: '1.74 MB',
    durationSeconds: 15.6,
    durationFormatted: '15s',
    createdAt: new Date(Date.now() - 3600000 * 30).toISOString(),
    createdAtFormatted: '2 days ago',
    result: 'likely_synthetic',
    confidencePercent: 65,
    summary:
      'The recording contains characteristics consistent with synthetic speech, though background noise limits certainty.',
    suspiciousSections: [
      {
        id: 'sec-1',
        startSeconds: 3.2,
        endSeconds: 5.4,
        startFormatted: '00:03.20',
        endFormatted: '00:05.40',
        confidencePercent: 72,
        label: 'Acoustic vocoder irregularity',
        evidenceSummary:
          'High-frequency phase discontinuity observed despite background street noise.',
      },
      {
        id: 'sec-2',
        startSeconds: 9.8,
        endSeconds: 12.1,
        startFormatted: '00:09.80',
        endFormatted: '00:12.10',
        confidencePercent: 68,
        label: 'Unnatural formant trajectory',
        evidenceSummary:
          'Unusual pitch transition profile during account balance recitation.',
      },
    ],
    evidenceCategories: [
      {
        id: 'ev-1',
        name: 'Speech characteristics',
        scorePercent: 67,
        bias: 'synthetic',
        explanation:
          'Synthetic speech markers identified in vocal formants above ambient noise floor.',
      },
      {
        id: 'ev-2',
        name: 'Voice pattern consistency',
        scorePercent: 62,
        bias: 'synthetic',
        explanation:
          'Moderate synthetic vocal tract patterns detected during speech bursts.',
      },
      {
        id: 'ev-3',
        name: 'Timing and rhythm',
        scorePercent: 55,
        bias: 'neutral',
        explanation:
          'Conversational cadence mixed with synthetic timing characteristics.',
      },
    ],
    conditions: {
      overallQuality: 'Moderate',
      speechAvailableDuration: '11.8 seconds',
      speechAvailableSeconds: 11.8,
      clarity: 'Moderate',
      recordingType: 'Compressed',
      sampleRateFormatted: '16.0 kHz',
      channelsFormatted: 'Mono (1 channel)',
      format: 'MP3 (Variable Bitrate)',
      notes:
        'Moderate acoustic interference and street noise in background.',
    },
    language: {
      detected: 'English',
      isCodeSwitching: false,
      isSupported: true,
    },
    provenance: {
      digitalCredentials: 'Not available',
      audioWatermark: 'Not detected',
      advisoryNote:
        'The absence of these credentials does not by itself indicate synthetic audio.',
    },
  },
};

export const MOCK_HISTORY_REPORTS: InvestigationReport[] = [
  MOCK_SCENARIOS['scenario-a'],
  MOCK_SCENARIOS['scenario-b'],
  MOCK_SCENARIOS['scenario-c'],
  MOCK_SCENARIOS['scenario-d'],
  {
    id: 'case-syn-9912',
    caseReference: 'CASE-2026-3190',
    recordingName: 'wire_transfer_authorisation_hinglish.wav',
    fileSizeBytes: 5120000,
    fileSizeFormatted: '4.88 MB',
    durationSeconds: 21.0,
    durationFormatted: '21s',
    createdAt: new Date(Date.now() - 3600000 * 48).toISOString(),
    createdAtFormatted: '3 days ago',
    result: 'likely_synthetic',
    confidencePercent: 91,
    summary:
      'The recording contains characteristics consistent with synthetic or cloned speech.',
    suspiciousSections: [
      {
        id: 'sec-1',
        startSeconds: 6.4,
        endSeconds: 9.8,
        startFormatted: '00:06.40',
        endFormatted: '00:09.80',
        confidencePercent: 95,
        label: 'Cloned bank manager voice spoof',
      },
    ],
    evidenceCategories: [
      {
        id: 'ev-1',
        name: 'Speech characteristics',
        scorePercent: 92,
        bias: 'synthetic',
        explanation: 'Deepfake neural vocoder signature present.',
      },
      {
        id: 'ev-2',
        name: 'Voice pattern consistency',
        scorePercent: 88,
        bias: 'synthetic',
        explanation: 'Mechanical harmonic distribution.',
      },
      {
        id: 'ev-3',
        name: 'Timing and rhythm',
        scorePercent: 71,
        bias: 'synthetic',
        explanation: 'Unnatural cadence.',
      },
    ],
    conditions: {
      overallQuality: 'Good',
      speechAvailableDuration: '21.0 seconds',
      speechAvailableSeconds: 21.0,
      clarity: 'High',
      recordingType: 'Clean',
      sampleRateFormatted: '24.0 kHz',
      channelsFormatted: 'Mono (1 channel)',
      format: 'WAV',
    },
    language: {
      detected: 'Hindi + English',
      isCodeSwitching: true,
      codeSwitchingDetails: 'Code-switching detected',
      isSupported: true,
    },
    provenance: {
      digitalCredentials: 'Not available',
      audioWatermark: 'Not detected',
      advisoryNote:
        'The absence of these credentials does not by itself indicate synthetic audio.',
    },
  },
  {
    id: 'case-hum-8821',
    caseReference: 'CASE-2026-1029',
    recordingName: 'branch_manager_inquiry_tamil.wav',
    fileSizeBytes: 3200100,
    fileSizeFormatted: '3.05 MB',
    durationSeconds: 16.5,
    durationFormatted: '16s',
    createdAt: new Date(Date.now() - 3600000 * 72).toISOString(),
    createdAtFormatted: '4 days ago',
    result: 'consistent_with_human',
    confidencePercent: 89,
    summary:
      'The recording does not show sufficient evidence of synthetic speech.',
    suspiciousSections: [],
    evidenceCategories: [
      {
        id: 'ev-1',
        name: 'Speech characteristics',
        scorePercent: 87,
        bias: 'human',
        explanation: 'Natural human vocal tract acoustics.',
      },
      {
        id: 'ev-2',
        name: 'Voice pattern consistency',
        scorePercent: 85,
        bias: 'human',
        explanation: 'Normal physiological breathing intervals.',
      },
      {
        id: 'ev-3',
        name: 'Timing and rhythm',
        scorePercent: 83,
        bias: 'human',
        explanation: 'Authentic conversational pacing.',
      },
    ],
    conditions: {
      overallQuality: 'Good',
      speechAvailableDuration: '16.5 seconds',
      speechAvailableSeconds: 16.5,
      clarity: 'High',
      recordingType: 'Clean',
      sampleRateFormatted: '16.0 kHz',
      channelsFormatted: 'Mono (1 channel)',
      format: 'WAV',
    },
    language: {
      detected: 'Tamil',
      isCodeSwitching: false,
      isSupported: true,
    },
    provenance: {
      digitalCredentials: 'Not available',
      audioWatermark: 'Not detected',
      advisoryNote:
        'The absence of these credentials does not by itself indicate synthetic audio.',
    },
  },
];
