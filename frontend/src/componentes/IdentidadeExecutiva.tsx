import React, { useEffect, useState } from "react";

/** Elementos exclusivamente visuais: não modificam decisões nem resultados. */
export function IconeMissao({ titulo }: { titulo: string }) {
  const texto = titulo.toLocaleLowerCase("pt-BR");
  const desenho = /pessoas|funcion|human|equipe|rh/.test(texto)
    ? "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 3a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-3.87M13 7a4 4 0 1 1-8 0a4 4 0 0 1 8 0"
    : /marketing|comerc|desenvolv|inova|tecnolog/.test(texto)
    ? "M12 3c5 0 8 3 9 8l-8 8-8-8c1-5 4-8 7-8M9 15l-4 4M5 15l-2 6 6-2M14 7h.01"
    : /finan|caixa|crédito|tribut|patrim/.test(texto)
    ? "M12 2v20M17 5H9a4 4 0 0 0 0 8h6a4 4 0 0 1 0 8H5"
    : /produ|opera|missão|rodada/.test(texto)
    ? "M13 2L3 14h8l-1 8 11-12h-8l1-8"
    : "M3 3v18h18M7 16l4-5 4 2 5-8";
  return <span className="icone-missao" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d={desenho}/></svg></span>;
}

export function SeloPodio({ posicao }: { posicao: number | null | undefined }) {
  const cores = ["bg-ouro/15 text-amber-900 ring-ouro/40", "bg-slate-100 text-slate-700 ring-slate-300", "bg-orange-100 text-orange-900 ring-orange-300"];
  return posicao && posicao <= 3 && posicao >= 1
    ? <span title={`${posicao}º lugar por patrimônio líquido`} className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ring-1 ${cores[posicao-1]}`}><span aria-hidden="true">✦</span>{posicao}º</span>
    : <span className="font-semibold text-corporativo">{posicao ? `${posicao}º` : "—"}</span>;
}

/** A barra descreve apenas a janela final de 24h. O servidor controla o prazo real. */
export function ProgressoPrazo({ prazo }: { prazo?: string | null }) {
  const [agora, setAgora] = useState(Date.now);
  useEffect(() => { if (!prazo) return; const id = window.setInterval(() => setAgora(Date.now()), 1000); return () => window.clearInterval(id); }, [prazo]);
  if (!prazo) return null;
  const limite = new Date(prazo).getTime();
  if (!Number.isFinite(limite)) return null;
  const restante = Math.max(0, limite - agora);
  const segundos = Math.floor(restante / 1000);
  const dias = Math.floor(segundos / 86400), horas = Math.floor(segundos % 86400 / 3600), minutos = Math.floor(segundos % 3600 / 60);
  const pct = Math.min(100, restante / 86400000 * 100);
  return <div className="prazo-executivo mt-4 rounded-xl border border-hub/20 bg-white p-4"><div className="flex flex-wrap justify-between gap-2 text-sm"><strong>{restante ? `Tempo restante: ${dias ? `${dias}d ` : ""}${horas}h ${minutos}min ${segundos % 60}s` : "Prazo atingido · aguardando atualização do servidor"}</strong><span className="text-slate-600">{new Intl.DateTimeFormat("pt-BR", {dateStyle:"short",timeStyle:"medium",timeZone:"America/Sao_Paulo"}).format(new Date(prazo))} · Brasília</span></div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label="Tempo restante nas últimas 24 horas" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)}><div className="h-full bg-hub transition-[width] duration-1000" style={{width:`${pct}%`}}/></div><p className="mt-2 text-xs text-slate-500">A barra acompanha as últimas 24 horas do prazo.</p></div>;
}
