/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        corporativo: "#034AA6",
        royal: "#0762D9",
        hub: "#0AADBF",
        marinho: "#034AA6", // Azul Royal — identidade oficial
        ouro: "#D9851E", // Laranja Ouro — identidade oficial
      },
    },
  },
  plugins: [],
};
