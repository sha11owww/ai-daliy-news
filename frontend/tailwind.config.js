/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#F5F0E8',
        card: '#EDE4D4',
        border: '#D4C5A9',
        'ink-light': '#8B7D6B',
        ink: '#5C4F3F',
        'ink-dark': '#2C2820',
      },
      fontFamily: {
        sans: ['"Noto Sans SC"', '"Source Han Sans SC"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
