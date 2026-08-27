/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // AutoAgent design tokens
        bg: '#0a0b0f',
        surface: '#111318',
        border: '#1e2130',
        muted: '#6b7280',
        accent: '#6366f1',
        'accent-dim': '#1e1f3d',
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444',
        // Tool type colors
        'tool-search': '#3b82f6',
        'tool-browse': '#14b8a6',
        'tool-code': '#f59e0b',
        'tool-file': '#10b981',
        'tool-http': '#8b5cf6',
        'tool-memory': '#ec4899',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
