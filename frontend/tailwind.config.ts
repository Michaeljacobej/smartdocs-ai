import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        sky: "#e0f2fe",
        clay: "#f6f0e8",
        ember: "#ef4444",
        moss: "#14532d",
      },
      boxShadow: {
        card: "0 20px 45px -22px rgba(15, 23, 42, 0.35)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(14px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        rise: "rise 500ms ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
