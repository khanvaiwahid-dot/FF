/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Garena color scheme - white/orange/red
        background: '#FFFFFF',
        card: '#FFFFFF',
        subtle: '#F5F5F5',
        primary: '#FF4500',        // Garena orange-red
        'primary-hover': '#E03E00',
        secondary: '#FF6B35',      // Lighter orange
        'secondary-hover': '#FF5520',
        accent: '#FFA500',         // Pure orange
        success: '#28A745',
        error: '#DC3545',
        warning: '#FFC107',
        info: '#17A2B8',
        border: 'rgba(0, 0, 0, 0.1)',
        input: 'rgba(0, 0, 0, 0.05)',
        ring: '#FF4500',
        foreground: '#212529',
        destructive: {
          DEFAULT: '#DC3545',
          foreground: '#FFFFFF'
        },
        muted: {
          DEFAULT: '#6C757D',
          foreground: '#495057'
        },
        popover: {
          DEFAULT: '#FFFFFF',
          foreground: '#212529'
        }
      },
      fontFamily: {
        'heading': ['Chivo', 'sans-serif'],
        'body': ['Manrope', 'sans-serif'],
        'mono': ['JetBrains Mono', 'monospace']
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'\n      },
      keyframes: {
        'accordion-down': {
          from: { height: 0 },
          to: { height: 'var(--radix-accordion-content-height)' }
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: 0 }
        }
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out'
      }
    }
  },
  plugins: [require('tailwindcss-animate')]
}