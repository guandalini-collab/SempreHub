/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        marinho: "#0B2545", // Azul Profundo — cor primária da marca
        ouro: "#C5A059", // Ouro Fosco — cor de acento
      },
    },
  },
  plugins: [],
};
