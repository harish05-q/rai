import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#15201c",
        field: "#f5f7f2",
        line: "#d9ded6",
        success: "#168a5b",
        warning: "#b86f00",
        accent: "#236b8e"
      },
      boxShadow: {
        soft: "0 16px 40px rgba(21, 32, 28, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
