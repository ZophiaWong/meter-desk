import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        meter: {
          ink: "#18212f",
          line: "#d7dde7",
          mint: "#1f9d7a",
          amber: "#b7791f",
          blue: "#3167b1",
        },
      },
    },
  },
  plugins: [],
};

export default config;
