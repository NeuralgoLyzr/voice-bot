import defaultTheme from 'tailwindcss/defaultTheme';

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    fontFamily: {
      'sans': ['"Inter"', ...defaultTheme.fontFamily.sans],
    },
    screens: {
      ...defaultTheme.screens,
      'sm': {'min': '300px', 'max': '600px'},
    },
    extend: {},
  },
  plugins: [],
};
