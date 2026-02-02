/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        // Custom colors for the feed
        karma: {
          gold: '#FFD700',
          bronze: '#CD7F32',
          silver: '#C0C0C0'
        }
      }
    },
  },
  plugins: [],
}
