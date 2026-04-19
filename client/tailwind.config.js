/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        display: ["Outfit", "sans-serif"],
        mono:    ["IBM Plex Mono", "monospace"],
        body:    ["DM Sans", "sans-serif"],
      },
      colors: {
        // Base surfaces
        void:    "#020408",
        obsidian:"#050c14",
        abyss:   "#070e18",
        // Cyan accent scale
        signal: {
          50:  "#ecfeff",
          100: "#cffafe",
          200: "#a5f3fc",
          300: "#67e8f9",
          400: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2",
          700: "#0e7490",
          800: "#155e75",
          900: "#164e63",
        },
        // Violet secondary
        neural: {
          300: "#c4b5fd",
          400: "#a78bfa",
          500: "#8b5cf6",
          600: "#7c3aed",
          700: "#6d28d9",
          800: "#5b21b6",
        },
        // Amber for warnings / entities
        data: {
          300: "#fcd34d",
          400: "#fbbf24",
          500: "#f59e0b",
        },
        // Emerald for success
        pulse: {
          400: "#34d399",
          500: "#10b981",
        },
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(rgba(6,182,212,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(6,182,212,0.04) 1px, transparent 1px)",
        "radial-void":
          "radial-gradient(ellipse at center, #070e18 0%, #020408 70%)",
        "radial-signal":
          "radial-gradient(ellipse at 50% 0%, rgba(6,182,212,0.12) 0%, transparent 60%)",
        "radial-neural":
          "radial-gradient(ellipse at 100% 100%, rgba(139,92,246,0.1) 0%, transparent 50%)",
        "gradient-signal":
          "linear-gradient(135deg, #06b6d4, #0891b2)",
        "gradient-neural":
          "linear-gradient(135deg, #8b5cf6, #7c3aed)",
        "gradient-data":
          "linear-gradient(135deg, #22d3ee, #8b5cf6)",
      },
      backgroundSize: {
        "grid-40": "40px 40px",
      },
      boxShadow: {
        "signal":   "0 0 20px rgba(6,182,212,0.25), 0 0 60px rgba(6,182,212,0.08)",
        "signal-lg":"0 0 40px rgba(6,182,212,0.3),  0 0 100px rgba(6,182,212,0.1)",
        "neural":   "0 0 20px rgba(139,92,246,0.25), 0 0 60px rgba(139,92,246,0.08)",
        "glass":    "0 8px 32px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.05)",
        "glass-lg": "0 20px 60px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.06)",
        "card":     "0 4px 24px rgba(0,0,0,0.5)",
      },
      borderColor: {
        "glass":        "rgba(255,255,255,0.06)",
        "glass-bright": "rgba(255,255,255,0.12)",
        "signal":       "rgba(6,182,212,0.3)",
        "signal-bright":"rgba(6,182,212,0.6)",
        "neural":       "rgba(139,92,246,0.3)",
      },
      animation: {
        "pulse-slow":  "pulse 3s cubic-bezier(0.4,0,0.6,1) infinite",
        "scan":        "scan 2s linear infinite",
        "grid-drift":  "grid-drift 20s linear infinite",
        "flicker":     "flicker 0.15s infinite",
        "cursor-blink":"cursor-blink 1s step-end infinite",
      },
      keyframes: {
        scan: {
          "0%":   { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
        "grid-drift": {
          "0%":   { backgroundPosition: "0 0" },
          "100%": { backgroundPosition: "40px 40px" },
        },
        flicker: {
          "0%, 19%, 21%, 23%, 25%, 54%, 56%, 100%": { opacity: 1 },
          "20%, 24%, 55%": { opacity: 0.6 },
        },
        "cursor-blink": {
          "0%, 100%": { opacity: 1 },
          "50%":      { opacity: 0 },
        },
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
