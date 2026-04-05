/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-dark': '#070b14',
        'card-bg': 'rgba(16, 26, 44, 0.7)',
        'accent-blue': '#0088ff',
        'accent-green': '#00ff88',
        'accent-red': '#ff3333',
        'accent-orange': '#ffaa00',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
