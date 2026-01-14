/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './apps/**/*.py',
  ],
  theme: {
    extend: {
      colors: {
        'ff-red': '#DC2626',
        'ff-red-dark': '#B91C1C',
        'ff-orange': '#EA580C',
        'ff-gray': '#374151',
      }
    },
  },
  plugins: [],
}
