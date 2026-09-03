module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        carbon: '#070809', panel: '#0d0f11', raised: '#121518', line: '#22272c', ink: '#f4f4f5',
        muted: '#b4b7bf', f1: '#ff1801', sector: '#b26bff', flag: '#facc15', good: '#22c55e',
        surface: '#0b0f14', accent: '#06b6d4', warm: '#f97316'
      },
      fontFamily: { display: ['"Barlow Condensed"', 'sans-serif'], body: ['"Titillium Web"', 'sans-serif'] },
      animation: { 'fade-in-up': 'fadeInUp 420ms ease-out both', 'float-slow': 'floatSlow 6s ease-in-out infinite' },
      keyframes: {
        fadeInUp: { '0%': { opacity: '0', transform: 'translateY(8px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        floatSlow: { '0%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-6px)' }, '100%': { transform: 'translateY(0)' } }
      }
    }
  },
  plugins: [],
}
