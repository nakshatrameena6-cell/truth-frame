import React, { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FilePlus,
  History,
  Settings as SettingsIcon,
  Sun,
  Moon,
  ShieldCheck,
  Menu,
  X,
  Plus,
  Building2,
  Lock,
} from 'lucide-react';
import { getStoredTheme, setStoredTheme, applyTheme, ThemeMode } from '../lib/theme';
import { cn } from '../lib/utils';

export const AppShell: React.FC = () => {
  const [theme, setTheme] = useState<ThemeMode>(getStoredTheme());
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const toggleTheme = () => {
    const next: ThemeMode = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    setStoredTheme(next);
  };

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/analyze', label: 'New Analysis', icon: FilePlus },
    { path: '/history', label: 'Analysis History', icon: History },
    { path: '/settings', label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <div className="min-h-screen bg-bg-app text-txt-main flex flex-col md:flex-row font-sans">
      {/* Mobile Top Header */}
      <div className="md:hidden flex items-center justify-between px-4 h-14 bg-bg-surface border-b border-border-subtle sticky top-0 z-50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand flex items-center justify-center text-white shadow-sm">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <span className="font-bold text-sm tracking-tight text-txt-main font-mono">
            PandaMIND
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleTheme}
            className="p-2 rounded bg-bg-surface-elevated border border-border-subtle text-txt-muted"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded bg-bg-surface-elevated border border-border-subtle text-txt-muted"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Sidebar (Desktop Persistent / Mobile Drawer) */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 w-64 bg-bg-surface border-r border-border-subtle flex flex-col justify-between transition-transform duration-200 md:static md:translate-x-0',
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Institution Header / Logo */}
          <div className="p-5 border-b border-border-subtle">
            <NavLink
              to="/"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-3 group select-none"
            >
              <div className="w-9 h-9 rounded-lg bg-brand flex items-center justify-center text-white shadow-subtle group-hover:bg-brand-hover transition-colors">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <div className="font-mono font-bold tracking-tight text-base text-txt-main">
                  PandaMIND
                </div>
                <div className="text-[10px] uppercase font-mono tracking-wider text-txt-dim font-medium">
                  Audio Investigation
                </div>
              </div>
            </NavLink>

            {/* Bank / Security Level Tag */}
            <div className="mt-3.5 px-2.5 py-1.5 rounded bg-bg-surface-elevated border border-border-subtle flex items-center gap-2 text-[11px] font-mono text-txt-muted">
              <Building2 className="w-3.5 h-3.5 text-brand shrink-0" />
              <span className="truncate">NBFC Fraud Unit</span>
              <span className="ml-auto w-2 h-2 rounded-full bg-emerald-500" title="System online" />
            </div>
          </div>

          {/* Navigation Links */}
          <div className="p-4 space-y-1 flex-1">
            <div className="text-[10px] font-mono uppercase text-txt-dim tracking-wider px-3 pb-2 font-semibold">
              Investigation Workspace
            </div>

            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.path === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(item.path);

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    'flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all select-none',
                    isActive
                      ? 'bg-brand/10 text-brand font-semibold border border-brand/25 shadow-xs'
                      : 'text-txt-muted hover:text-txt-main hover:bg-bg-surface-hover'
                  )}
                >
                  <Icon className={cn('w-4 h-4', isActive ? 'text-brand' : 'text-txt-dim')} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>

          {/* Primary Quick CTA in Sidebar */}
          <div className="p-4 border-t border-border-subtle space-y-3">
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                navigate('/analyze');
              }}
              className="w-full py-2.5 px-3 rounded-lg bg-brand hover:bg-brand-hover text-white text-xs font-semibold shadow-subtle flex items-center justify-center gap-2 transition-all active:scale-[0.99]"
            >
              <Plus className="w-4 h-4" />
              <span>+ New Analysis</span>
            </button>

            {/* Analyst & Compliance footer info */}
            <div className="px-2 pt-2 text-[10px] font-mono text-txt-dim flex items-center justify-between border-t border-border-subtle/50">
              <div className="flex items-center gap-1">
                <Lock className="w-3 h-3 text-txt-dim" />
                <span>Audit Logged</span>
              </div>
              <span>v1.0 Bank Suite</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area with Top Bar */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Desktop Top Header Bar */}
        <header className="hidden md:flex h-14 bg-bg-surface/85 backdrop-blur border-b border-border-subtle sticky top-0 z-30 px-6 items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-xs font-mono text-txt-muted">
            <span className="text-txt-dim">PandaMIND</span>
            <span>/</span>
            <span className="text-txt-main font-semibold capitalize">
              {location.pathname === '/'
                ? 'Dashboard'
                : location.pathname.split('/')[1]?.replace('-', ' ')}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Quick Link to New Analysis */}
            <button
              onClick={() => navigate('/analyze')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand hover:bg-brand-hover text-white text-xs font-semibold shadow-subtle transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Analysis</span>
            </button>

            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg bg-bg-surface-elevated border border-border-subtle text-txt-muted hover:text-txt-main hover:bg-bg-surface-hover transition-colors"
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </header>

        {/* Viewport content */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>

      {/* Backdrop for mobile drawer */}
      {mobileMenuOpen && (
        <div
          onClick={() => setMobileMenuOpen(false)}
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
        />
      )}
    </div>
  );
};
