import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getHealth } from '../api/health';
import { getModelInfo } from '../api/model';
import { getAudioFormats } from '../api/formats';
import { isMockModeEnabled, setMockModeEnabled, resetMockDataToDefault } from '../api/client';
import { Settings as SettingsIcon, Cpu, Activity, FileAudio, Database, RefreshCw, CheckCircle2, AlertTriangle } from 'lucide-react';
import { ConfirmDialog } from '../components/ConfirmDialog';

export const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [useMock, setUseMock] = useState(isMockModeEnabled());
  const [isResetConfirmOpen, setIsResetConfirmOpen] = useState(false);

  const { data: health, isLoading: isHealthLoading, refetch: refetchHealth } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
  });

  const { data: model, isLoading: isModelLoading } = useQuery({
    queryKey: ['modelInfo'],
    queryFn: getModelInfo,
  });

  const { data: formats } = useQuery({
    queryKey: ['audioFormats'],
    queryFn: getAudioFormats,
  });

  const handleToggleMock = (enabled: boolean) => {
    setUseMock(enabled);
    setMockModeEnabled(enabled);
    queryClient.invalidateQueries();
  };

  const handleResetData = () => {
    resetMockDataToDefault();
    queryClient.invalidateQueries();
    setIsResetConfirmOpen(false);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto font-sans">
      {/* Page Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-brand" />
          <h1 className="text-xl font-bold font-mono tracking-tight text-txt-main">
            System & Engine Settings
          </h1>
        </div>
        <p className="text-xs text-txt-muted font-sans">
          Configure API connection parameters, inspection engine modes, and inspect backend health diagnostic endpoints.
        </p>
      </div>

      {/* 1. Execution Engine Mode Toggle Card */}
      <div className="rounded-lg border border-border-strong bg-bg-surface p-6 space-y-4 shadow-panel">
        <div className="flex items-center gap-2 pb-3 border-b border-border-subtle">
          <Database className="w-4 h-4 text-brand" />
          <h3 className="text-sm font-mono font-bold text-txt-main">Execution Engine Provider</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Option A: Embedded Mock Engine */}
          <div
            onClick={() => handleToggleMock(true)}
            className={`p-4 rounded-lg border cursor-pointer transition-all space-y-2 select-none ${
              useMock
                ? 'border-brand bg-brand-subtle shadow-subtle'
                : 'border-border-subtle bg-bg-surface-elevated hover:border-brand/40'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-txt-main">Embedded Simulation Engine</span>
              {useMock && <CheckCircle2 className="w-4 h-4 text-brand" />}
            </div>
            <p className="text-[11px] font-mono text-txt-muted leading-relaxed">
              Runs in-memory simulation with realistic queued → processing state transitions and pre-seeded evaluation test records.
            </p>
          </div>

          {/* Option B: Live REST API Backend */}
          <div
            onClick={() => handleToggleMock(false)}
            className={`p-4 rounded-lg border cursor-pointer transition-all space-y-2 select-none ${
              !useMock
                ? 'border-brand bg-brand-subtle shadow-subtle'
                : 'border-border-subtle bg-bg-surface-elevated hover:border-brand/40'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-txt-main">Live Python REST API (/api/v1)</span>
              {!useMock && <CheckCircle2 className="w-4 h-4 text-brand" />}
            </div>
            <p className="text-[11px] font-mono text-txt-muted leading-relaxed">
              Connects directly to active FastAPI backend endpoint at <code className="text-brand">http://localhost:8000</code>.
            </p>
          </div>
        </div>

        {useMock && (
          <div className="pt-2 flex items-center justify-between">
            <span className="text-xs font-mono text-txt-dim">Reset local mock store to seed data:</span>
            <button
              onClick={() => setIsResetConfirmOpen(true)}
              className="px-3 py-1.5 rounded bg-bg-surface-elevated border border-border-subtle text-txt-muted hover:text-txt-main text-xs font-mono transition-colors flex items-center gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reset Mock Dataset</span>
            </button>
          </div>
        )}
      </div>

      {/* 2. Backend Health & Model Diagnostics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Backend Health Diagnostics */}
        <div className="rounded-lg border border-border-strong bg-bg-surface p-5 space-y-3 shadow-panel">
          <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-txt-main">
              <Activity className="w-4 h-4 text-brand" />
              <span>Backend Health (GET /health)</span>
            </div>
            <button
              onClick={() => refetchHealth()}
              className="p-1 rounded text-txt-dim hover:text-txt-main hover:bg-bg-surface-elevated transition-colors"
              title="Refresh health"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between py-1 border-b border-border-subtle">
              <span className="text-txt-dim">System Status</span>
              <span className="font-semibold text-emerald-400 uppercase">{health?.status || 'OK'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-border-subtle">
              <span className="text-txt-dim">Engine Version</span>
              <span className="text-txt-main">{health?.version || '1.0.0'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-border-subtle">
              <span className="text-txt-dim">Detector Model Loaded</span>
              <span className="text-emerald-400 font-semibold">{health?.model_loaded ? 'TRUE' : 'FALSE'}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-txt-dim">Active Model Version</span>
              <span className="text-amber-500 font-semibold">{health?.model_version || 'phase9-experimental'}</span>
            </div>
          </div>
        </div>

        {/* Model Calibration Info */}
        <div className="rounded-lg border border-border-strong bg-bg-surface p-5 space-y-3 shadow-panel">
          <div className="flex items-center gap-2 pb-2 border-b border-border-subtle text-xs font-mono font-bold text-txt-main">
            <Cpu className="w-4 h-4 text-brand" />
            <span>Detector Protocol (GET /api/v1/model)</span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between py-1 border-b border-border-subtle">
              <span className="text-txt-dim">Model Name</span>
              <span className="text-txt-main">{model?.name || 'PandaMIND Detector'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-border-subtle">
              <span className="text-txt-dim">Calibration Status</span>
              <span className="text-emerald-400 uppercase">{model?.calibration_status || 'Calibrated'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-border-subtle">
              <span className="text-txt-dim">Low Threshold (θ_low)</span>
              <span className="text-txt-main font-bold">{model?.thresholds.low || 0.7408}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-txt-dim">High Threshold (θ_high)</span>
              <span className="text-txt-main font-bold">{model?.thresholds.high || 0.7556}</span>
            </div>
          </div>
        </div>

      </div>

      {/* 3. Supported Audio Formats Card */}
      <div className="rounded-lg border border-border-strong bg-bg-surface p-5 space-y-3 shadow-panel">
        <div className="flex items-center gap-2 pb-2 border-b border-border-subtle text-xs font-mono font-bold text-txt-main">
          <FileAudio className="w-4 h-4 text-brand" />
          <span>Supported Audio Stream Constraints (GET /api/v1/audio/formats)</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
          <div className="p-3 rounded bg-bg-surface-elevated border border-border-subtle">
            <span className="text-[10px] text-txt-dim uppercase block">Allowed Extensions</span>
            <span className="font-semibold text-brand font-mono">
              {formats?.supported_extensions.join(', ') || '.wav, .mp3, .flac, .ogg, .m4a'}
            </span>
          </div>

          <div className="p-3 rounded bg-bg-surface-elevated border border-border-subtle">
            <span className="text-[10px] text-txt-dim uppercase block">Max File Payload</span>
            <span className="font-semibold text-txt-main font-mono">25 MB (26,214,400 bytes)</span>
          </div>

          <div className="p-3 rounded bg-bg-surface-elevated border border-border-subtle">
            <span className="text-[10px] text-txt-dim uppercase block">Max Audio Duration</span>
            <span className="font-semibold text-txt-main font-mono">300 seconds (5.0 minutes)</span>
          </div>
        </div>
      </div>

      {/* Confirm Reset Dialog */}
      <ConfirmDialog
        isOpen={isResetConfirmOpen}
        title="Reset Mock Dataset"
        description="Are you sure you want to reset the mock database? All custom uploaded audio evaluations will be cleared and restored to the default 6 seed test cases."
        confirmLabel="Reset Dataset"
        isDestructive={true}
        onConfirm={handleResetData}
        onCancel={() => setIsResetConfirmOpen(false)}
      />
    </div>
  );
};
