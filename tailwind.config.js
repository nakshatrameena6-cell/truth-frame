/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: {
          app: 'var(--bg-app)',
          surface: 'var(--bg-surface)',
          elevated: 'var(--bg-surface-elevated)',
          hover: 'var(--bg-surface-hover)',
          active: 'var(--bg-surface-active)',
        },
        border: {
          subtle: 'var(--border-subtle)',
          strong: 'var(--border-strong)',
          focus: 'var(--border-focus)',
        },
        txt: {
          main: 'var(--text-main)',
          muted: 'var(--text-muted)',
          dim: 'var(--text-dim)',
          inv: 'var(--text-inv)',
        },
        brand: {
          DEFAULT: 'var(--accent-brand)',
          hover: 'var(--accent-brand-hover)',
          subtle: 'var(--accent-brand-subtle)',
        },
        verdict: {
          human: {
            DEFAULT: 'var(--verdict-human)',
            bg: 'var(--verdict-human-bg)',
            border: 'var(--verdict-human-border)',
          },
          inconclusive: {
            DEFAULT: 'var(--verdict-inconclusive)',
            bg: 'var(--verdict-inconclusive-bg)',
            border: 'var(--verdict-inconclusive-border)',
          },
          synthetic: {
            DEFAULT: 'var(--verdict-synthetic)',
            bg: 'var(--verdict-synthetic-bg)',
            border: 'var(--verdict-synthetic-border)',
          },
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
      borderRadius: {
        sm: '4px',
        DEFAULT: '6px',
        md: '8px',
        lg: '10px',
      },
      boxShadow: {
        subtle: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        panel: '0 4px 12px -2px rgba(0, 0, 0, 0.08)',
      },
    },
  },
  plugins: [],
};
