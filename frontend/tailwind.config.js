/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        clinical: {
          teal: {
            50: "#f0fdfa",
            100: "#ccfbf1",
            200: "#99f6e4",
            500: "#14b8a6",
            600: "#0d9488",
            700: "#0f766e",
            800: "#115e59",
            900: "#134e4a",
          },
          navy: {
            50: "#f8fafc",
            100: "#f1f5f9",
            700: "#334155",
            800: "#1e293b",
            900: "#0f172a",
          }
        }
      }
    },
  },
  plugins: [],
}
