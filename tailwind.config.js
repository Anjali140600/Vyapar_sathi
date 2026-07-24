/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        slateDeep: "#1E293B",
        ivory: "#FDF6EC",
        income: "#10B981",
        expense: "#F43F5E",
        insight: "#F59E0B",
        assistant: "#0EA5E9",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
      },
      boxShadow: {
        soft: "0 18px 60px rgba(15, 23, 42, 0.12)",
        glow: "0 0 0 1px rgba(255,255,255,0.08), 0 20px 80px rgba(14, 165, 233, 0.18)",
      },
      fontFamily: {
        sans: ["DM Sans", "sans-serif"],
        display: ["Sora", "Plus Jakarta Sans", "DM Sans", "sans-serif"],
      },
      backgroundImage: {
        "hero-grid":
          "radial-gradient(circle at top left, rgba(16,185,129,0.18), transparent 28%), radial-gradient(circle at top right, rgba(14,165,233,0.18), transparent 24%), linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02))",
      },
    },
  },
  plugins: [],
};
