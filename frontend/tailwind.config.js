/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        marinho: "#102A68", // Azul Profundo — cor primária da marca
        ouro: "#FFC233", // Amarelo vivo — cor de acento
      },
    },
  },
  plugins: [],
};
