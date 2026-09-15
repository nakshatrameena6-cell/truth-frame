export type InvestigationResult =
  | 'likely_synthetic'
  | 'consistent_with_human'
  | 'inconclusive';

export interface SuspiciousSection {
  id: string;
  startSeconds: number;
  endSeconds: number;
  startFormatted: string; // e.g. "04:12"
  endFormatted: string;   // e.g. "06:89"
  confidencePercent: number; // e.g. 94
  label: string;
  evidenceSummary?: string;
}

export interface EvidenceCategory {
  id: string;
  name: string; // 'Speech characteristics', 'Voice pattern consistency', 'Timing and rhythm'
  scorePercent: number; // 0 - 100
  bias: 'synthetic' | 'human' | 'neutral';
  explanation: string;
}

export interface RecordingConditions {
  overallQuality: 'Good' | 'Moderate' | 'Degraded' | 'Limited';
  speechAvailableDuration: string; // e.g. "18.4 seconds"
  speechAvailableSeconds: number;
  clarity: 'High' | 'Moderate' | 'Low';
  recordingType: 'Clean' | 'Compressed' | 'Telecom' | 'Studio';
  sampleRateFormatted: string;
  channelsFormatted: string;
  format: string;
  notes?: string;
}

export interface LanguageDetection {
  detected: string; // e.g. "Hindi + English" or "Tamil"
  isCodeSwitching: boolean;
  codeSwitchingDetails?: string; // e.g. "Code-switching detected"
  isSupported: boolean;
  guidanceNote?: string;
}

export interface RecordingProvenance {
  digitalCredentials: 'Not available' | 'Verified' | 'Invalid';
  audioWatermark: 'Not detected' | 'Detected' | 'Tampered';
  advisoryNote: string;
}

export interface InvestigationReport {
  id: string;
  caseReference?: string;
  recordingName: string;
  fileSizeBytes: number;
  fileSizeFormatted: string;
  durationSeconds: number;
  durationFormatted: string;
  createdAt: string;
  createdAtFormatted: string;
  
  result: InvestigationResult;
  confidencePercent: number | null; // Strictly NULL for 'inconclusive'
  summary: string;
  
  audioUrl?: string;
  suspiciousSections: SuspiciousSection[];
  evidenceCategories: EvidenceCategory[];
  conditions: RecordingConditions;
  language: LanguageDetection;
  provenance: RecordingProvenance;
}

export type ScenarioId = 'scenario-a' | 'scenario-b' | 'scenario-c' | 'scenario-d';
