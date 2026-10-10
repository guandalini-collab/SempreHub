import LinkManual from "./LinkManual";
import React from "react";
import {manuais} from "./MenuManuais";

export default function CentralManuais({perfil}: {perfil: "ALUNO" | "PROFESSOR"}) {
  return <div className="grid gap-4 sm:grid-cols-2">
    {manuais.filter(m => perfil === "PROFESSOR" || m.arquivo !== "manual-professor").map(m =>
      <article key={m.arquivo} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-lg font-bold">{m.titulo}</h3>
        <p className="my-3 text-sm text-slate-600">{m.descricao}</p>
        <div className="flex flex-wrap gap-3">
          <LinkManual className="rounded-lg bg-marinho px-4 py-3 text-sm font-semibold text-white" arquivo={m.arquivo} baixar aria-label={`Baixar PDF: ${m.titulo}`}>Baixar PDF</LinkManual>
          <LinkManual className="rounded-lg border border-slate-300 px-4 py-3 text-sm font-semibold" arquivo={m.arquivo} aria-label={`Visualizar: ${m.titulo}`}>Visualizar</LinkManual>
        </div>
      </article>
    )}
  </div>;
}
