import LinkManual from "./LinkManual";
import React, {useEffect, useRef} from "react";

export const manuais = [
  {arquivo: "manual-aluno", titulo: "Manual do aluno", descricao: "Equipes, decisões, mercado e resultados."},
  {arquivo: "manual-professor", titulo: "Manual do professor", descricao: "Turmas, rodadas e avaliação."},
  {arquivo: "manual-midias", titulo: "Manual de mídias e campanhas", descricao: "Canais, serviços e planejamento de campanhas."},
];

export default function MenuManuais({perfil}: {perfil?: string}) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const fechar = (evento: PointerEvent) => {
      if (!ref.current?.contains(evento.target as Node)) ref.current?.removeAttribute("open");
    };
    document.addEventListener("pointerdown", fechar);
    return () => document.removeEventListener("pointerdown", fechar);
  }, []);
  return <details ref={ref} className="relative z-50 shrink-0 text-sm" onKeyDown={e => {
    if (e.key === "Escape") {ref.current?.removeAttribute("open");ref.current?.querySelector("summary")?.focus();}
  }}>
    <summary className="cursor-pointer rounded-lg border border-white/40 px-3 py-2 font-semibold text-white hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ouro">Manuais</summary>
    <nav aria-label="Manuais em PDF" className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-xl bg-white p-4 text-marinho shadow-xl ring-1 ring-slate-200">
      <p className="mb-3 font-bold">Baixar manuais em PDF</p>
      <ul className="space-y-3">{manuais.filter(m => perfil !== "ALUNO" || m.arquivo !== "manual-professor").map(m => <li key={m.arquivo} className="border-t border-slate-200 pt-3">
        <p className="font-semibold">{m.titulo}</p>
        <p className="mt-1 text-xs text-slate-600">{m.descricao}</p>
        <div className="mt-2 flex gap-4 text-xs font-semibold">
          <LinkManual arquivo={m.arquivo} baixar className="rounded bg-marinho px-3 py-2 text-white hover:bg-blue-800" aria-label={`Baixar PDF: ${m.titulo}`}>Baixar PDF</LinkManual>
          <LinkManual arquivo={m.arquivo} className="py-2 underline" aria-label={`Visualizar: ${m.titulo}`}>Visualizar</LinkManual>
        </div>
      </li>)}</ul>
    </nav>
  </details>;
}
