import React, { useState } from 'react';
import { Building2, ShieldCheck, Sparkles, Sliders, Bell, FileText, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getStoredTheme, setStoredTheme, applyTheme, ThemeMode } from '../lib/theme';

export const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const [theme, setTheme] = useState<ThemeMode>(getStoredTheme());
  const [casePrefix, setCasePrefix] = useState('CASE-2026');
  const [unitName, setUnitName] = useState('Financial Crimes & Voice Forensics Unit');
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleThemeChange = (newTheme: ThemeMode) => {
    setTheme(newTheme);
    setStoredTheme(newTheme);
    applyTheme(newTheme);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-150 py-2">
      {/* Header */}
      <div className="border-b border-border-subtle pb-5">
        <h1 className="text-2xl font-bold tracking-tight text-txt-main">
          Settings & Preferences
        </h1>
        <p className="text-xs text-txt-muted mt-1">
          Configure investigation session standards, evidentiary policies, and environment defaults
        </p>
      </div>

      {saveSuccess && (
        <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 flex items-center gap-2.5 text-xs text-emerald-400 font-mono animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          <span>Investigation preferences saved successfully.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Section 1: Investigation Unit Configuration */}
        <div className="bg-bg-surface p-6 rounded-lg border border-border-subtle space-y-4">
          <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
            <Building2 className="w-4 h-4 text-brand" />
            <h2 className="text-sm font-semibold text-txt-main">
              Investigation Unit Profile
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-mono text-txt-muted uppercase text-[10px] mb-1">
                Investigation Department / Unit
              </label>
              <input
                type="text"
                value={unitName}
                onChange={(e) => setUnitName(e.target.value)}
                className="w-full px-3.5 py-2 rounded-md bg-bg-surface-elevated border border-border-subtle text-txt-main focus:ring-1 focus:ring-brand font-mono"
              />
            </div>

            <div>
              <label className="block font-mono text-txt-muted uppercase text-[10px] mb-1">
                Default Case Reference Prefix
              </label>
              <input
                type="text"
                value={casePrefix}
                onChange={(e) => setCasePrefix(e.target.value)}
                className="w-full px-3.5 py-2 rounded-md bg-bg-surface-elevated border border-border-subtle text-txt-main focus:ring-1 focus:ring-brand font-mono"
              />
            </div>
          </div>
        </div>

        {/* Section 2: Mock Scenarios Quick Access */}
        <div className="bg-bg-surface p-6 rounded-lg border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand" />
              <h2 className="text-sm font-semibold text-txt-main">
                Benchmark Investigation Scenarios
              </h2>
            </div>
            <span className="text-[11px] font-mono text-txt-dim">
              Offline Demonstration
            </span>
          </div>

          <p className="text-xs text-txt-muted leading-relaxed">
            Inspect canonical evidentiary scenarios directly to review how different determination bands, confidence thresholds, and suspicious segments present to analysts.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <button
              type="button"
              onClick={() => navigate('/analysis/scenario-a')}
              className="p-3 rounded-lg bg-bg-surface-elevated border border-border-subtle hover:border-rose-500/50 hover:bg-bg-surface-hover text-left transition-colors group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-rose-400">
                  Scenario A — Synthetic
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  87% Conf
                </span>
              </div>
              <p className="text-xs text-txt-muted mt-1">
                Likely Synthetic with 2 localized suspicious speech sections and Hindi+English code-switching.
              </p>
            </button>

            <button
              type="button"
              onClick={() => navigate('/analysis/scenario-b')}
              className="p-3 rounded-lg bg-bg-surface-elevated border border-border-subtle hover:border-emerald-500/50 hover:bg-bg-surface-hover text-left transition-colors group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-emerald-400">
                  Scenario B — Human
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  92% Conf
                </span>
              </div>
              <p className="text-xs text-txt-muted mt-1">
                Consistent with genuine human speech in Tamil with natural biological acoustics.
              </p>
            </button>

            <button
              type="button"
              onClick={() => navigate('/analysis/scenario-c')}
              className="p-3 rounded-lg bg-bg-surface-elevated border border-border-subtle hover:border-amber-500/50 hover:bg-bg-surface-hover text-left transition-colors group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-amber-400">
                  Scenario C — Inconclusive
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  Abstention
                </span>
              </div>
              <p className="text-xs text-txt-muted mt-1">
                Acoustic signal degraded by telecom compression. Strictly abstains without manufactured probability.
              </p>
            </button>

            <button
              type="button"
              onClick={() => navigate('/analysis/scenario-d')}
              className="p-3 rounded-lg bg-bg-surface-elevated border border-border-subtle hover:border-purple-500/50 hover:bg-bg-surface-hover text-left transition-colors group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-purple-400">
                  Scenario D — Difficult Recording
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  65% Conf
                </span>
              </div>
              <p className="text-xs text-txt-muted mt-1">
                Likely Synthetic with ambient background interference and multiple flagged segments.
              </p>
            </button>
          </div>
        </div>

        {/* Section 3: Interface & Theme */}
        <div className="bg-bg-surface p-6 rounded-lg border border-border-subtle space-y-4">
          <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
            <Sliders className="w-4 h-4 text-brand" />
            <h2 className="text-sm font-semibold text-txt-main">
              Interface & Accessibility
            </h2>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold text-txt-main block">
                Visual Theme Mode
              </span>
              <p className="text-xs text-txt-muted mt-0.5">
                Select between high-contrast Dark Mode and institution Light Mode
              </p>
            </div>

            <div className="flex items-center gap-1 bg-bg-surface-elevated p-1 rounded-lg border border-border-subtle">
              <button
                type="button"
                onClick={() => handleThemeChange('dark')}
                className={`px-3 py-1 text-xs font-mono rounded ${
                  theme === 'dark'
                    ? 'bg-brand text-white font-bold'
                    : 'text-txt-muted hover:text-txt-main'
                }`}
              >
                Dark
              </button>
              <button
                type="button"
                onClick={() => handleThemeChange('light')}
                className={`px-3 py-1 text-xs font-mono rounded ${
                  theme === 'light'
                    ? 'bg-brand text-white font-bold'
                    : 'text-txt-muted hover:text-txt-main'
                }`}
              >
                Light
              </button>
            </div>
          </div>
        </div>

        {/* Section 4: Audit & Regulatory Compliance */}
        <div className="bg-bg-surface p-6 rounded-lg border border-border-subtle space-y-3">
          <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            <h2 className="text-sm font-semibold text-txt-main">
              Regulatory Audit & Evidence Chain
            </h2>
          </div>

          <p className="text-xs text-txt-muted leading-relaxed">
            PandaMIND maintains an immutable audit log of audio hashes, timestamps, and investigation determinations. Inconclusive determinations are strictly logged as non-evaluable abstentions in accordance with banking anti-fraud guidelines.
          </p>
        </div>

        {/* Submit */}
        <div className="flex justify-end">
          <button
            type="submit"
            className="px-5 py-2 rounded-lg bg-brand hover:bg-brand-hover text-white text-xs font-semibold shadow-subtle transition-colors"
          >
            Save Preferences
          </button>
        </div>
      </form>
    </div>
  );
};
