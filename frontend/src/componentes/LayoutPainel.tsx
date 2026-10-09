import React, { useEffect, useRef, useState } from "react";

export interface ItemPainel {
  id: string;
  titulo: string;
  descricao: string;
  simbolo: string;
  grupo?: string;
  estado?: string;
  pai?: string;
}
export function SecaoPainel({
  id,
  ativa,
  children,
}: {
  id: string;
  ativa: string;
  children: React.ReactNode;
}) {
  return (
    <section id={`secao-${id}`} hidden={ativa !== id} className="space-y-6">
      {children}
    </section>
  );
}
export default function LayoutPainel({
  itens,
  ativa,
  aoSelecionar,
  rodada,
  total,
  concluidas,
  perfil,
  contexto,
  children,
}: {
  itens: ItemPainel[];
  ativa: string;
  aoSelecionar: (id: string) => void;
  rodada: number;
  total: number;
  concluidas: number;
  perfil: string;
  contexto?: { turma: string; empresa?: string; status: string; codigo?: string; caixa?: number; alertas?: number };
  children: React.ReactNode;
}) {
  const grupoAtivo = itens.find(i => i.id === ativa)?.grupo ?? "Menu";
  const grupos = [...new Set(itens.map(i => i.grupo ?? "Menu"))];
  const [gruposAbertos, setGruposAbertos] = useState<string[]>(grupos);
  useEffect(() => {
    setGruposAbertos(anteriores => anteriores.includes(grupoAtivo) ? anteriores : [...anteriores, grupoAtivo]);
  }, [ativa, grupoAtivo, perfil]);

  const titulo = useRef<HTMLHeadingElement>(null);
  const anterior = useRef(ativa);
  useEffect(() => {
    if (anterior.current !== ativa) {
      titulo.current?.focus();
      anterior.current = ativa;
    }
  }, [ativa]);
  const item = itens.find((i) => i.id === ativa) ?? itens.find(i => i.id === "visao") ?? itens[0];
  const progresso = Math.min(
    100,
    Math.round((concluidas / Math.max(1, total)) * 100),
  );
  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(220px,1fr)_minmax(0,3fr)]">
      <aside className="max-h-[55dvh] overflow-y-auto rounded-2xl bg-marinho p-4 text-white shadow-lg lg:sticky lg:top-4 lg:max-h-[calc(100dvh-2rem)]">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-widest text-ouro">
            {perfil}
          </p>

        </div>
        <nav
          id="menu-painel"
          aria-label={`Navegação do ${perfil}`}
          className="mt-4 space-y-1"
        >
          <button type="button" aria-current={ativa === "manuais" ? "page" : undefined} aria-controls="secao-manuais" onClick={() => aoSelecionar("manuais")} className={`mb-2 w-full rounded-lg border border-ouro/50 px-3 py-3 text-left text-sm font-bold ${ativa === "manuais" ? "bg-ouro text-marinho" : "text-white hover:bg-white/10"}`}>Manuais · baixar PDF</button>
          {grupos.filter(grupo => grupo !== "Manuais").map((grupo, indice) => {
            const expandido = gruposAbertos.includes(grupo);
            const contemAtiva = grupoAtivo === grupo;
            return <div key={grupo} className="py-1">
              <button type="button" aria-expanded={expandido} aria-controls={`submenu-${indice}`} onClick={() => setGruposAbertos(anteriores => expandido ? anteriores.filter(g => g !== grupo) : [...anteriores, grupo])} className={`flex w-full items-center justify-between rounded-lg px-3 py-3 text-left text-sm font-bold focus-visible:outline focus-visible:outline-2 focus-visible:outline-ouro ${contemAtiva ? "bg-blue-700 text-white" : "text-blue-100 hover:bg-white/10"}`}>
                <span>{grupo}</span><span aria-hidden="true">{expandido ? "▾" : "▸"}</span>
              </button>
              <div id={`submenu-${indice}`} hidden={!expandido} className="ml-3 mt-2 space-y-1 border-l-2 border-blue-300/40 pl-2">
                {itens.filter(i => (i.grupo ?? "Menu") === grupo && !i.pai).map(i => <React.Fragment key={i.id}><button type="button" key={i.id} aria-current={ativa === i.id ? "page" : undefined} aria-controls={`secao-${i.id}`} title={i.descricao} onClick={() => { aoSelecionar(i.id); }} className={`w-full rounded-lg px-3 py-3 text-left text-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-ouro ${ativa === i.id ? "bg-ouro font-bold text-marinho" : "text-white hover:bg-white/10"}`}><span className="block">{i.titulo}</span>{i.estado && <span className="mt-1 block text-[11px] opacity-80">{i.estado}</span>}</button>{itens.some(f => f.pai === i.id) && <div className="ml-3 space-y-1 border-l border-white/30 pl-2" aria-label={`Submenu de ${i.titulo}`}>{itens.filter(f => f.pai === i.id).map(f => <button key={f.id} type="button" aria-current={ativa === f.id ? "page" : undefined} aria-controls={`secao-${f.id}`} onClick={() => aoSelecionar(f.id)} className={`w-full rounded-lg px-3 py-2 text-left text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-ouro ${ativa === f.id ? "bg-ouro font-bold text-marinho" : "text-blue-100 hover:bg-white/10"}`}>{f.titulo}</button>)}</div>}</React.Fragment>)}
              </div>
            </div>;
          })}
        </nav>
        {perfil === "Aluno" && <div className="mt-5 rounded-xl border border-white/20 bg-white/5 p-3"><h3 className="text-sm font-bold">Checklist de Validação da Rodada</h3><ul className="mt-3 space-y-2 text-xs">{itens.filter(i=>i.estado).map(i=><li key={i.id}><button type="button" className="w-full text-left" onClick={()=>aoSelecionar(i.id)}>{i.estado === "Decisão pendente" ? "○" : "✓"} {i.titulo}<span className="block pl-4 text-white/70">{i.estado}</span></button></li>)}</ul></div>}
        <div className="mt-5 hidden border-t border-white/15 pt-4 lg:block">
          <p className="text-sm font-semibold">Jornada empresarial</p>
          <p className="mt-1 text-xs text-white/70">
            Rodada {Math.min(rodada, total)} de {total} · {concluidas}{" "}
            concluída(s)
          </p>
          <div
            role="progressbar"
            aria-label="Rodadas concluídas"
            aria-valuenow={progresso}
            aria-valuemin={0}
            aria-valuemax={100}
            className="mt-3 h-2 overflow-hidden rounded-full bg-white/15"
          >
            <div
              className="h-full bg-ouro transition-all"
              style={{ width: `${progresso}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-white/70">
            {progresso}% da simulação concluída
          </p>
        </div>
      </aside>
      <div className="min-w-0 space-y-6">
        {contexto && <div className="sticky top-0 z-30 rounded-xl border border-blue-200 bg-white/95 p-4 shadow-sm backdrop-blur" aria-label="Turma e rodada atual">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Turma</p><p className="text-lg font-bold">{contexto.turma}</p>{contexto.empresa && <p className="text-sm text-slate-600">Sua empresa: {contexto.empresa}</p>}{contexto.codigo && <p className="text-sm text-slate-600">Código de entrada: <strong className="font-mono">{contexto.codigo}</strong></p>}</div>
            <div className="flex flex-wrap items-center gap-3">{contexto.caixa !== undefined && <div><p className="text-xs text-slate-500">Caixa disponível</p><p className={`text-xl font-bold tabular-nums ${contexto.caixa >= 0 ? "text-emerald-700" : "text-red-700"}`}>{contexto.caixa.toLocaleString("pt-BR", {style:"currency",currency:"BRL"})}</p><p className="text-xs text-amber-800">{contexto.alertas ? `${contexto.alertas} pendência(s) de consistência` : "Sem pendências registradas"}</p></div>}<div><p className="font-bold text-blue-700">Rodada {Math.min(rodada, total)} de {total}</p><p className="text-sm text-slate-600">{contexto.status}</p></div><button type="button" onClick={() => { const grupo = itens.find(i => i.id === "rodada")?.grupo ?? "Menu"; setGruposAbertos(anteriores => anteriores.includes(grupo) ? anteriores : [...anteriores, grupo]); aoSelecionar("rodada"); }} hidden={perfil === "Professor"} className="rounded-lg bg-blue-700 px-4 py-3 text-sm font-bold text-white hover:bg-blue-800">Abrir rodada atual →</button><a href="#/" className="rounded-lg border border-slate-300 px-3 py-3 text-sm font-semibold">Trocar turma</a></div>
          </div>
        </div>}
        <header>
          <h2
            ref={titulo}
            tabIndex={-1}
            className="text-2xl font-bold outline-none"
          >
            {item.titulo}
          </h2>
          <p className="mt-1 text-sm text-slate-600">{item.descricao}</p>
        </header>
        {children}
      </div>
    </div>
  );
}
