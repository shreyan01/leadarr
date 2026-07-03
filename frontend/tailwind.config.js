/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Base surfaces — deep slate-navy, not pure black. Distinct from
        // the generic near-black-with-one-accent AI default.
        canvas: "#0B0E14",
        surface: "#12161F",
        "surface-raised": "#181D29",
        border: "#242B3A",
        "border-subtle": "#1A2030",
        // Text
        ink: "#E7E9EE",
        "ink-muted": "#8B93A7",
        "ink-faint": "#5B6478",
        // Signature accent — warm brass/amber, reads as "opportunity /
        // value found", distinct from Claude's terracotta and from
        // generic acid-green-on-black.
        brass: {
          DEFAULT: "#C99A44",
          bright: "#E0B563",
          dim: "#8A6C34",
        },
        // Priority scale — used consistently for lead priority + score bands
        priority: {
          critical: "#E5484D",
          high: "#E0932F",
          medium: "#4C8DFF",
          low: "#5B6478",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        card: "10px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.03)",
      },
    },
  },
  plugins: [],
};
