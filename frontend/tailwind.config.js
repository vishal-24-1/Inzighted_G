// tailwind.config.js
module.exports = {
  content: [
    // Tell Tailwind to scan all JavaScript, JSX, TypeScript, and HTML files
    // in your src folder for class names.
    './src/**/*.{js,jsx,ts,tsx}',
    './public/index.html',
  ],
  theme: {
    extend: {
      fontFamily: {
        // make Tenorite available as 'tenorite' and the default 'sans' stack
        tenorite: ['Tenorite', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial'],
        sans: ['Tenorite', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial'],
      },
    },
  },
  plugins: [],
};