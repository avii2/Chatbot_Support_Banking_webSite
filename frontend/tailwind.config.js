/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: '#0A2342',
          teal: '#2CA58D',
          cream: '#F7F3E9',
          coral: '#F25F5C'
        }
      },
      fontFamily: {
        display: ['Sora', 'sans-serif'],
        body: ['Manrope', 'sans-serif']
      },
      boxShadow: {
        soft: '0 16px 38px -24px rgba(10, 35, 66, 0.55)'
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        pulseDot: {
          '0%, 80%, 100%': { opacity: '0.2', transform: 'translateY(0)' },
          '40%': { opacity: '1', transform: 'translateY(-3px)' }
        }
      },
      animation: {
        fadeUp: 'fadeUp 450ms ease-out both',
        pulseDot: 'pulseDot 1s infinite ease-in-out'
      }
    }
  },
  plugins: []
}
