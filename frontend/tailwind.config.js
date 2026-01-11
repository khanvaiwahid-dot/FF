/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#0B0B0F',
        card: '#121218',
        subtle: '#1A1A24',
        primary: '#00F0FF',
        'primary-hover': '#00C2CC',
        secondary: '#B026FF',
        'secondary-hover': '#8A1CC4',
        accent: '#FFBA00',
        success: '#00FF94',
        error: '#FF2E2E',
        warning: '#FFBA00',
        info: '#00F0FF',
        border: 'rgba(255, 255, 255, 0.05)',
        input: 'rgba(255, 255, 255, 0.05)',
        ring: 'hsl(var(--ring))',
        foreground: 'hsl(var(--foreground))',
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))'
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))'
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))'
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
        sm: 'calc(var(--radius) - 4px)'
      },
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