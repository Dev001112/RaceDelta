module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        surface: '#0b0f14',
        muted: '#94a3b8',
        accent: '#06b6d4',
        warm: '#f97316'
      },
      animation: {
        'fade-in-up': 'fadeInUp 420ms ease-out both',
        'float-slow': 'floatSlow 6s ease-in-out infinite'
      },
      keyframes: {
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        floatSlow: {
          '0%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
          '100%': { transform: 'translateY(0)' }
        }
      }
    }
  },
  plugins: [],
}
