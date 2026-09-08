import React, { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { AudioLines, History, Settings as SettingsIcon, Sun, Moon, ShieldCheck } from 'lucide-react';
import { ModelStatusBadge } from './ModelStatusBadge';
import { getStoredTheme, setStoredTheme, applyTheme, ThemeMode } from '../lib/theme';
import { cn } from '../lib/utils';

export const AppShell: React.FC = () => {
  const [theme, setTheme] = useState<ThemeMode>(getStoredTheme());
  const location = useLocation();

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const toggleTheme = () => {
    const next: ThemeMode = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    setStoredTheme(next);
  };

  const navItems = [
    { path: '/analyze', label: 'Analyze', icon: AudioLines },
    { path: '/history', label: 'History', icon: History },
    { path: '/settings', label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <div className="min-h-screen bg-bg-app text-txt-main flex flex-col font-sans">
      {/* Top Header Navigation */}
      <header className="sticky top-0 z-40 bg-bg-surface/90 backdrop-blur border-b border-border-subtle">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-4">
          
          {/* Brand Logo & Wordmark */}
          <div className="flex items-center gap-6">
            <NavLink to="/analyze" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded bg-brand flex items-center justify-center text-white shadow-subtle group-hover:bg-brand-hover transition-colors">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div className="flex flex-col">
                <span className="font-mono font-bold tracking-tight text-sm text-txt-main group-hover:text-brand transition-colors">
                  PandaMIND
                </span>
                <span className="text-[10px] font-mono text-txt-dim tracking-wider uppercase -mt-1">
                  Audio Workspace
                </span>
              </div>
            </NavLink>

            {/* Navigation Tabs */}
            <nav className="flex items-center gap-1 ml-4" aria-label="Main Navigation">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path || (item.path === '/analyze' && location.pathname === '/');
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={cn(
                      'flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-colors select-none',
                      isActive
                        ? 'bg-bg-surface-elevated text-brand font-semibold border border-border-subtle'
                        : 'text-txt-muted hover:text-txt-main hover:bg-bg-surface-hover'
                    )}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>
          </div>

          {/* Right Header Metadata & Controls */}
          <div className="flex items-center gap-3">
            <ModelStatusBadge className="hidden md:inline-flex" />

            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded bg-bg-surface-elevated border border-border-subtle text-txt-muted hover:text-txt-main hover:bg-bg-surface-hover transition-colors"
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </main>

      {/* Analyst Technical Footer */}
      <footer className="border-t border-border-subtle bg-bg-surface/50 py-3 text-xs text-txt-dim font-mono">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>PandaMIND Engine v1.0.0</span>
            <span>·</span>
            <span>Deterministic Calibration Active</span>
          </div>
          <div>
            <span>Backend API Base: <code className="text-txt-muted">/api/v1</code></span>
          </div>
        </div>
      </footer>
    </div>
  );
};
