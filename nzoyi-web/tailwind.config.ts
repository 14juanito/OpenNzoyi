import type { Config } from "tailwindcss";

// Palette OpenNzoyi — extraite du logo (abeille orange sur fond clair).
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        nzoyi: {
          orange: "#F59E0B",   // accent principal (abeille)
          amber: "#EAB308",    // variante accent
          ink: "#1F2937",      // noir profond (texte / structure)
          slate: "#6B7280",    // texte secondaire
          bg: "#F8F9FA",       // fond principal
          card: "#FFFFFF",     // cartes
          success: "#10B981",  // succès
          danger: "#EF4444",   // alerte
          border: "#E5E7EB",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
      },
    },
  },
  plugins: [],
};

export default config;
