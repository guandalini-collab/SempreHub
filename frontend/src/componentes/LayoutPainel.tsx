import React, { useEffect, useRef, useState } from "react";

export interface ItemPainel {
  id: string;
  titulo: string;
  descricao: string;
  simbolo: string;
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
  children,
}: {
  itens: ItemPainel[];
  ativa: string;
  aoSelecionar: (id: string) => void;
  rodada: number;
  total: number;
  concluidas: number;
  perfil: string;
  children: React.ReactNode;
}) {
  const [aberto, setAberto] = useState(false);
  const titulo = useRef<HTMLHeadingElement>(null);
  const anterior = useRef(ativa);
  useEffect(() => {
    if (anterior.current !== ativa) {
      titulo.current?.focus();
      anterior.current = ativa;
    }
    setAberto(false);
  }, [ativa]);
  useEffect(() => {
    const fechar = (e: KeyboardEvent) => {
      if (e.key === "Escape") setAberto(false);
    };
    window.addEventListener("keydown", fechar);
    return () => window.removeEventListener("keydown", fechar);
  }, []);
  const item = itens.find((i) => i.id === ativa) ?? itens[0];
  const progresso = Math.min(
    100,
    Math.round((concluidas / Math.max(1, total)) * 100),
  );
  return (
    <div className="grid items-start gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
      <aside className="rounded-2xl bg-marinho p-4 text-white shadow-lg lg:sticky lg:top-4">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-widest text-ouro">
            {perfil}
          </p>
          <button
            type="button"
            className="rounded border border-white/30 px-3 py-2 text-sm lg:hidden"
            aria-expanded={aberto}
            aria-controls="menu-painel"
            onClick={() => setAberto(!aberto)}
          >
            {aberto ? "Fechar menu" : "Abrir menu"}
          </button>
        </div>
        <nav
          id="menu-painel"
          aria-label={`Navegação do ${perfil}`}
          className={`${aberto ? "block" : "hidden"} mt-4 space-y-1 lg:block`}
        >
          {itens.map((i) => (
            <button
              type="button"
              key={i.id}
              aria-current={ativa === i.id ? "page" : undefined}
              aria-controls={`secao-${i.id}`}
              onClick={() => {
                setAberto(false);
                aoSelecionar(i.id);
              }}
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-ouro ${ativa === i.id ? "bg-ouro text-marinho" : "text-white/80 hover:bg-white/10"}`}
            >
              <span aria-hidden="true" className="w-5 text-center">
                {i.simbolo}
              </span>
              {i.titulo}
            </button>
          ))}
        </nav>
        <div className="mt-5 border-t border-white/15 pt-4">
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
