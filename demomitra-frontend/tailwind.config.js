/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cream: '#F7F4EF',
        beige: '#EDEAE3',
        softGray: '#F1F1F1',
        darkText: '#3E3E3E',
        aubergine: '#6C4675',
        aubergineDark: '#59325C',
        taupe: '#D4CFC7',
      },
      fontFamily: {
        sans: ['"Inter"', 'sans-serif'],
      },
      borderRadius: {
        xl: '1rem',
        '2xl': '1.5rem',
      },
    },
  },
  plugins: [],
};
