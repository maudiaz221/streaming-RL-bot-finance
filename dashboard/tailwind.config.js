/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Base colors
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        
        // Card
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
          border: 'hsl(var(--card-border))',
        },
        
        // UI states
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        
        // Neon accent colors
        'neon-cyan': 'hsl(var(--neon-cyan))',
        'neon-magenta': 'hsl(var(--neon-magenta))',
        'neon-purple': 'hsl(var(--neon-purple))',
        'neon-green': 'hsl(var(--neon-green))',
        'neon-red': 'hsl(var(--neon-red))',
        'neon-orange': 'hsl(var(--neon-orange))',
        'neon-yellow': 'hsl(var(--neon-yellow))',
        
        // Coin-specific
        btc: 'hsl(var(--btc))',
        eth: 'hsl(var(--eth))',
        bnb: 'hsl(var(--bnb))',
      },
      
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Monaco', 'monospace'],
        display: ['Orbitron', 'sans-serif'],
      },
      
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'gradient-shift': 'gradient-shift 8s ease infinite',
        'slide-in': 'slide-in 0.3s ease-out',
        'flash-green': 'flash-green 0.3s ease-out',
        'flash-red': 'flash-red 0.3s ease-out',
      },
      
      backdropBlur: {
        xs: '2px',
      },
      
      boxShadow: {
        'glow-cyan': '0 0 10px hsl(var(--neon-cyan) / 0.3), 0 0 30px hsl(var(--neon-cyan) / 0.2)',
        'glow-magenta': '0 0 10px hsl(var(--neon-magenta) / 0.3), 0 0 30px hsl(var(--neon-magenta) / 0.2)',
        'glow-green': '0 0 10px hsl(var(--neon-green) / 0.3), 0 0 30px hsl(var(--neon-green) / 0.2)',
        'glow-red': '0 0 10px hsl(var(--neon-red) / 0.3), 0 0 30px hsl(var(--neon-red) / 0.2)',
      },
    },
  },
  plugins: [],
}
