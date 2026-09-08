export type ThemeMode = 'dark' | 'light' | 'system';

const STORAGE_KEY_THEME = 'pandamind_theme_mode';

export function getStoredTheme(): ThemeMode {
  const val = localStorage.getItem(STORAGE_KEY_THEME) as ThemeMode | null;
  return val || 'dark';
}

export function setStoredTheme(theme: ThemeMode): void {
  localStorage.setItem(STORAGE_KEY_THEME, theme);
  applyTheme(theme);
}

export function applyTheme(theme: ThemeMode): void {
  const root = document.documentElement;
  const isSystemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  if (theme === 'dark' || (theme === 'system' && isSystemDark)) {
    root.classList.add('dark');
    root.classList.remove('light');
  } else {
    root.classList.remove('dark');
    root.classList.add('light');
  }
}
