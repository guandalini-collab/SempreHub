import React, { useEffect, useState } from "react";
import { reais, percentual } from "../formatos";
import type { PainelAluno } from "../tipos";
import { Botao, Cartao, EntradaNumero, Modal } from "./ui";
export interface Jornada {
  rodadas_concluidas: number;
  conquistas: {
    id: string;
    titulo: string;
    descricao: string;
    rodada: number | null;
    obtida: boolean;
  }[];
  feed: {
    id: string;
    rodada: number;
    titulo: string;
    texto: string;
    lucro: number;
    participacao: number;
  }[];
}
export function ControleVisual({
  valor,
  aoMudar,
  minimo = 0,
  limite,
  moeda = true,
  inteiro = false,
  rotulo,
}: {
  valor: number;
  aoMudar: (n: number) => void;
  minimo?: number;
  limite: number;
  moeda?: boolean;
  inteiro?: boolean;
  rotulo: string;
}) {
  const teto = Math.max(limite, valor, minimo + 1);
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="mb-3 text-2xl font-bold tabular-nums">
        {moeda ? reais(valor) : valor}
      </div>
      <input
        aria-label={rotulo}
        type="range"
        min={minimo}
        max={teto}
        step={inteiro ? 1 : 0.01}
        value={valor}
        onChange={(e) => aoMudar(Number(e.target.value))}
        className="w-full accent-[#C5A059]"
      />
      <details className="mt-2">
        <summary className="cursor-pointer text-xs font-medium text-slate-600">
          Ajustar valor exato
        </summary>
        <div className="mt-2">
          <EntradaNumero
            aria-label={`${rotulo} — valor exato`}
            valor={valor}
            aoMudar={aoMudar}
            minimo={minimo}
            moeda={moeda}
            inteiro={inteiro}
          />
        </div>
      </details>
    </div>
  );
}
export function ResumoNegocio({
  painel,
  aoResultados,
}: {
  painel: PainelAluno;
  aoResultados: () => void;
}) {
  const r = painel.resultados[painel.resultados.length - 1];
  const alerta = painel.empresa.fase_atual === "SOBREVIVENCIA";
  const tom = alerta
    ? "border-red-200 bg-red-50 text-red-800"
    : r && r.dre.lucro_liquido < 0
      ? "border-amber-200 bg-amber-50 text-amber-900"
      : "border-emerald-200 bg-emerald-50 text-emerald-900";
  return (
    <Cartao titulo="Seu negócio em um olhar">
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          ["Caixa disponível", reais(painel.empresa.caixa)],
          [
            "Resultado do mês",
            r ? reais(r.dre.lucro_liquido) : "Aguardando rodada",
          ],
          [
            "Participação de mercado",
            r ? percentual(r.participacao_mercado) : "Aguardando rodada",
          ],
        ].map(([nome, valor]) => (
          <div key={nome} className="rounded-2xl bg-slate-50 p-4">
            <p className="text-xs text-slate-500">{nome}</p>
            <p className="mt-2 text-2xl font-bold tabular-nums">{valor}</p>
          </div>
        ))}
      </div>
      <div className={`my-4 rounded-xl border p-4 ${tom}`}>
        <p className="font-semibold">
          {alerta
            ? "Crítico · reserva de caixa insuficiente"
            : r && r.dre.lucro_liquido < 0
              ? "Atenção · esta rodada terminou com prejuízo"
              : r
                ? "Rodada com resultado positivo ou equilibrado"
                : "Sua primeira rodada começa com uma decisão"}
        </p>
        <p className="mt-1 text-sm">
          {alerta
            ? "O caixa não cobre um mês de custos fixos. Consulte a prévia e os demonstrativos."
            : "Compare a evolução do caixa, do resultado e da participação para orientar suas escolhas."}
        </p>
      </div>
      <Botao variante="secundario" onClick={aoResultados}>
        Explorar resultados e demonstrativos
      </Botao>
    </Cartao>
  );
}
export function Conquistas({ jornada }: { jornada?: Jornada }) {
  return (
    <Cartao titulo="Conquistas da sua jornada">
      <p className="mb-5 text-sm text-slate-500">
        Marcos conquistados pelas decisões e pelos resultados registrados. Cada
        empresa constrói sua própria trajetória.
      </p>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {jornada?.conquistas.map((c) => (
          <article
            key={c.id}
            className={`rounded-2xl border p-5 ${c.obtida ? "border-ouro bg-amber-50" : "border-slate-200 bg-slate-50"}`}
          >
            <span
              aria-hidden="true"
              className={`mb-3 inline-flex h-12 w-12 items-center justify-center rounded-full text-2xl ${c.obtida ? "bg-ouro text-marinho" : "bg-slate-200 text-slate-500"}`}
            >
              {c.obtida ? "★" : "◇"}
            </span>
            <h3 className="font-bold">{c.titulo}</h3>
            <p className="mt-2 text-sm text-slate-600">{c.descricao}</p>
            <p className="mt-3 text-xs font-semibold">
              {c.obtida ? `Conquistada na rodada ${c.rodada}` : "Próximo marco"}
            </p>
          </article>
        ))}
      </div>
      {!jornada && <p>Carregando os marcos da sua empresa…</p>}
    </Cartao>
  );
}
export function FeedResultados({
  jornada,
  aoResultados,
}: {
  jornada?: Jornada;
  aoResultados: () => void;
}) {
  return (
    <Cartao titulo="O mercado respondeu">
      <p className="mb-4 text-sm text-slate-500">
        Acontecimentos da sua empresa, com base nos resultados da simulação.
      </p>
      <div className="space-y-3">
        {jornada?.feed.map((f) => (
          <article
            key={f.id}
            className="rounded-2xl border border-slate-200 p-4"
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Sua empresa · rodada {f.rodada}
            </p>
            <h3 className="mt-2 text-lg font-bold">{f.titulo}</h3>
            <p className="my-2 text-sm text-slate-600">{f.texto}</p>
            <p className="mb-3 text-sm">
              Resultado: <strong>{reais(f.lucro)}</strong> · Mercado:{" "}
              <strong>{percentual(f.participacao)}</strong>
            </p>
            <Botao variante="secundario" onClick={aoResultados}>
              Explorar resultado
            </Botao>
          </article>
        ))}
      </div>
      {!jornada?.feed.length && (
        <p className="text-sm text-slate-500">
          Sua primeira manchete aparecerá após o fechamento da rodada.
        </p>
      )}
    </Cartao>
  );
}
export function ViradaRodada({
  painel,
  podeAbrir = true,
}: {
  painel: PainelAluno;
  podeAbrir?: boolean;
}) {
  const r = painel.resultados[painel.resultados.length - 1];
  const [aberta, setAberta] = useState(false),
    [etapa, setEtapa] = useState(0);
  const chave = `semprehub.virada.${painel.empresa.id}`;
  useEffect(() => {
    if (!r || !podeAbrir) return;
    try {
      if (Number(localStorage.getItem(chave) ?? 0) < r.rodada) {
        setEtapa(0);
        setAberta(true);
      }
    } catch {
      /* replay continua disponível */
    }
  }, [chave, r?.rodada, podeAbrir]);
  function fechar() {
    setAberta(false);
    if (r) {
      try {
        localStorage.setItem(chave, String(r.rodada));
      } catch {
        /* opcional */
      }
    }
  }
  if (!r) return null;
  return (
    <>
      <Botao
        variante="secundario"
        onClick={() => {
          setEtapa(0);
          setAberta(true);
        }}
      >
        Rever a virada · rodada {r.rodada}
      </Botao>
      {aberta && (
        <Modal
          titulo={`O mercado respondeu · rodada ${r.rodada}`}
          aoFechar={fechar}
        >
          <div className="py-6 text-center">
            <p className="text-xs uppercase tracking-widest text-slate-500">
              {painel.empresa.nome}
            </p>
            <h2 className="my-4 text-3xl font-bold">
              {
                [
                  "Suas decisões encontraram o mercado",
                  "As vendas chegaram",
                  "O resultado da rodada",
                  "Sua posição na competição",
                ][etapa]
              }
            </h2>
            <p className="my-8 text-4xl font-bold text-marinho">
              {etapa === 0
                ? `Rodada ${r.rodada} concluída`
                : etapa === 1
                  ? `${r.unidades_vendidas} unidades vendidas`
                  : etapa === 2
                    ? reais(r.dre.lucro_liquido)
                    : `${percentual(r.participacao_mercado)} do mercado`}
            </p>
            <div
              className="mb-5 flex justify-center gap-2"
              aria-label={`Etapa ${etapa + 1} de 4`}
            >
              {[0, 1, 2, 3].map((i) => (
                <span
                  key={i}
                  className={`h-2 w-10 rounded-full ${i <= etapa ? "bg-ouro" : "bg-slate-200"}`}
                />
              ))}
            </div>
            <Botao onClick={() => (etapa < 3 ? setEtapa(etapa + 1) : fechar())}>
              {etapa < 3
                ? "Revelar próximo resultado"
                : "Continuar minha jornada"}
            </Botao>
            <button
              type="button"
              onClick={fechar}
              className="ml-4 text-sm text-slate-500 underline"
            >
              Pular apresentação
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
