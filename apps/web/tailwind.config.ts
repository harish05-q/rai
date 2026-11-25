import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#20382b",
        field: "#edf2e7",
        line: "#cbd9c8",
        success: "#168a5b",
        warning: "#b86f00",
        accent: "#376344"
      },
      boxShadow: {
        soft: "0 16px 40px rgba(32, 56, 43, 0.055)"
      }
    }
  },
  plugins: []
};

export default config;
