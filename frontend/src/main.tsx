import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import "./index.css";

// Campos numéricos nativos: ao digitar sobre o 0, o navegador mantinha o zero à
// esquerda ("05000"), embora o valor gravado fosse 5000. Depois que o React trata
// o evento, o texto do campo é normalizado (defeito relatado em 22/11/2026).
document.addEventListener("input", (evento) => {
  const campo = evento.target;
  if (!(campo instanceof HTMLInputElement) || campo.type !== "number") return;
  const limpo = campo.value.replace(/^(-?)0+(?=\d)/, "$1");
  if (limpo !== campo.value) campo.value = limpo;
});

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
