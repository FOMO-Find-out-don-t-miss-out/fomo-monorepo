/** @type {import('tailwindcss').Config} */
module.exports = {
  // Required by NativeWind 4.x — bridges Tailwind utilities to React Native StyleSheet
  presets: [require('nativewind/preset')],
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        'neon-purple': '#BC13FE',
        'neon-cyan': '#22D3EE',
        'neon-pink': '#EC4899',
        obsidian: '#0B0B0F',
      },
    },
  },
  plugins: [],
};
