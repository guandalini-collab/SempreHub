import React, { useCallback, useEffect, useState } from "react";

import logoSempreHub from "./assets/SempreHub.jpg";

export type FaseAtual =
  | "IDEACAO"
  | "PLANEJAMENTO"
  | "CAPTACAO"
  | "OPERACAO_ESTAVEL"
  | "SOBREVIVENCIA";

export type RegimeTributario = "MEI" | "SIMPLES_NACIONAL" | "LUCRO_PRESUMIDO";

export interface EventoCrise {
  titulo: string;
  narrativa: string;
  consequencias: Record<string, string | number | boolean>;
}

export interface DemonstrativoResultado {
  receitaBruta: number;
  custoPessoalClt: number;
  custoCmv: number;
  impostoPago: number;
}

export interface PontoCaixaMes {
  mes: number;
  caixa: number;
}

export interface EmpresaResumo {
  regime_tributario: RegimeTributario;
  faturamento_acumulado_ano: number;
  desenquadrado_mei: boolean;
}

export interface DetalhesRodada {
  unidades_vendidas: number;
  cmv_turnos_restantes: number;
  penalizado_posicionamento_porter: boolean;
}

export interface RespostaAvancarTurno {
  session_id: number;
  mes_atual: number;
  fase_atual: FaseAtual;
  caixa_atual: number;
  autoeficacia: number;
  necessidade_realizacao: number;
  networking: number;
  empresa: EmpresaResumo;
  demonstrativo: DemonstrativoResultado;
  detalhes_rodada: DetalhesRodada;
  evento: EventoCrise | null;
}

const REGIME_LABELS: Record<RegimeTributario, string> = {
  MEI: "MEI",
  SIMPLES_NACIONAL: "Simples Nacional",
  LUCRO_PRESUMIDO: "Lucro Presumido",
};

const formatarReais = (valor: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(valor);

interface UsarSempreHubResultado {
  estado: RespostaAvancarTurno | null;
  historicoCaixa: PontoCaixaMes[];
  carregando: boolean;
  erro: string | null;
  avancarTurno: () => Promise<void>;
}

export function useSempreHub(sessionId: number, apiBaseUrl = ""): UsarSempreHubResultado {
  const [estado, setEstado] = useState<RespostaAvancarTurno | null>(null);
  const [historicoCaixa, setHistoricoCaixa] = useState<PontoCaixaMes[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const avancarTurno = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const resposta = await fetch(`${apiBaseUrl}/partidas/${sessionId}/avancar-turno`, {
        method: "POST",
      });

      if (!resposta.ok) {
        throw new Error(`Falha ao avançar turno (HTTP ${resposta.status})`);
      }

      const dados: RespostaAvancarTurno = await resposta.json();
      setEstado(dados);
      setHistoricoCaixa((atual) => [...atual, { mes: dados.mes_atual, caixa: dados.caixa_atual }]);
    } catch (erroRequisicao) {
      setErro(
        erroRequisicao instanceof Error
          ? erroRequisicao.message
          : "Erro desconhecido ao avançar turno."
      );
    } finally {
      setCarregando(false);
    }
  }, [sessionId, apiBaseUrl]);

  return { estado, historicoCaixa, carregando, erro, avancarTurno };
}

function ProgressBar({ label, valor }: { label: string; valor: number }) {
  const percentual = Math.min(100, Math.max(0, valor));
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-200">
        <span>{label}</span>
        <span>{percentual.toFixed(0)}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-white/20">
        <div
          className="h-full rounded-full bg-[#C5A059] transition-all"
          style={{ width: `${percentual}%` }}
        />
      </div>
    </div>
  );
}

function LinhaDemonstrativo({ label, valor }: { label: string; valor: number }) {
  const positivo = valor >= 0;
  return (
    <tr className="border-b border-slate-100">
      <td className="py-2 text-sm text-slate-600">{label}</td>
      <td
        className={`py-2 text-right text-sm font-medium ${
          positivo ? "text-emerald-600" : "text-red-600"
        }`}
      >
        {formatarReais(valor)}
      </td>
    </tr>
  );
}

function construirPontosGrafico(
  dados: PontoCaixaMes[],
  largura: number,
  altura: number
): string {
  if (dados.length === 0) return "";
  const valores = dados.map((ponto) => ponto.caixa);
  const minCaixa = Math.min(...valores);
  const maxCaixa = Math.max(...valores);
  const amplitude = maxCaixa - minCaixa || 1;

  return dados
    .map((ponto, indice) => {
      const x = dados.length === 1 ? 0 : (indice / (dados.length - 1)) * largura;
      const y = altura - ((ponto.caixa - minCaixa) / amplitude) * altura;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

function EvolucaoCaixaChart({ historicoCaixa }: { historicoCaixa: PontoCaixaMes[] }) {
  const LARGURA = 300;
  const ALTURA = 140;

  if (historicoCaixa.length === 0) {
    return <p className="text-sm text-slate-400">Sem histórico suficiente para exibir o gráfico.</p>;
  }

  const pontos = construirPontosGrafico(historicoCaixa, LARGURA, ALTURA);
  const valores = historicoCaixa.map((ponto) => ponto.caixa);
  const primeiro = historicoCaixa[0];
  const ultimo = historicoCaixa[historicoCaixa.length - 1];

  return (
    <div>
      <div className="mb-2 flex justify-between text-xs text-slate-500">
        <span>Máx.: {formatarReais(Math.max(...valores))}</span>
        <span>Mín.: {formatarReais(Math.min(...valores))}</span>
      </div>
      <svg
        viewBox={`0 0 ${LARGURA} ${ALTURA}`}
        className="w-full"
        role="img"
        aria-label="Gráfico de evolução do caixa ao longo dos meses"
      >
        {[0.25, 0.5, 0.75].map((fracao) => (
          <line
            key={fracao}
            x1={0}
            x2={LARGURA}
            y1={ALTURA * fracao}
            y2={ALTURA * fracao}
            stroke="#0B2545"
            strokeOpacity={0.08}
            strokeWidth={1}
          />
        ))}
        <polyline points={pontos} fill="none" stroke="#C5A059" strokeWidth={2.5} />
        {historicoCaixa.map((ponto, indice) => {
          const [x, y] = pontos.split(" ")[indice].split(",").map(Number);
          return <circle key={ponto.mes} cx={x} cy={y} r={2.5} fill="#0B2545" />;
        })}
      </svg>
      <div className="mt-2 flex justify-between text-xs text-slate-500">
        <span>Mês {primeiro.mes}</span>
        <span>Mês {ultimo.mes}</span>
      </div>
    </div>
  );
}

export interface DashboardProps {
  sessionId: number;
  apiBaseUrl?: string;
}

export default function Dashboard({ sessionId, apiBaseUrl }: DashboardProps) {
  const { estado, historicoCaixa, carregando, erro, avancarTurno } = useSempreHub(
    sessionId,
    apiBaseUrl
  );

  const [modalAberto, setModalAberto] = useState(false);

  useEffect(() => {
    setModalAberto(Boolean(estado?.evento));
  }, [estado]);

  const evento = estado?.evento ?? null;
  const consequenciasEvento = evento ? Object.entries(evento.consequencias) : [];

  const demonstrativo = estado?.demonstrativo;
  const resultadoPeriodo = demonstrativo
    ? demonstrativo.receitaBruta -
      demonstrativo.custoPessoalClt -
      demonstrativo.custoCmv -
      demonstrativo.impostoPago
    : 0;

  return (
    <div className="min-h-screen bg-slate-100 p-6 font-sans text-[#0B2545]">
      <header className="rounded-xl bg-[#0B2545] p-6 text-white shadow-lg">
        <div className="mb-6 flex items-center gap-4 border-b border-white/10 pb-5">
          <img
            src={logoSempreHub}
            alt="Logotipo SempreHub"
            className="h-14 w-14 shrink-0 rounded-lg object-contain ring-1 ring-[#C5A059]/40"
          />
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">SempreHub</h1>
            <p className="text-xs uppercase tracking-[0.2em] text-[#C5A059]">
              Ecossistema de Aceleração de Negócios
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap gap-8">
            <div>
              <p className="text-xs uppercase tracking-wide text-white/60">Caixa Atual</p>
              <p className="text-2xl font-bold text-[#C5A059]">
                {estado ? formatarReais(estado.caixa_atual) : "—"}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-white/60">Mês Atual</p>
              <p className="text-2xl font-bold">{estado ? `Mês ${estado.mes_atual}` : "—"}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-white/60">Regime Tributário</p>
              <p className="text-2xl font-bold">
                {estado ? REGIME_LABELS[estado.empresa.regime_tributario] : "—"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {estado?.fase_atual === "SOBREVIVENCIA" && (
              <span className="animate-pulse rounded-full bg-red-600 px-4 py-2 text-sm font-bold uppercase tracking-wide text-white shadow-lg shadow-red-900/50">
                Alerta: Estado de Sobrevivência de Dornelas
              </span>
            )}
            <button
              onClick={avancarTurno}
              disabled={carregando}
              className="rounded-lg bg-[#C5A059] px-5 py-2.5 text-sm font-semibold text-[#0B2545] shadow transition hover:bg-[#C5A059]/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {carregando ? "Processando..." : "Avançar Turno"}
            </button>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <ProgressBar label="Autoeficácia" valor={estado?.autoeficacia ?? 0} />
          <ProgressBar label="Necessidade de Realização" valor={estado?.necessidade_realizacao ?? 0} />
          <ProgressBar label="Networking" valor={estado?.networking ?? 0} />
        </div>
      </header>

      {erro && (
        <div className="mt-4 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
          {erro}
        </div>
      )}

      {!estado ? (
        <div className="mt-6 rounded-xl bg-white p-10 text-center text-slate-500 shadow-md">
          Nenhum turno jogado ainda. Clique em "Avançar Turno" para começar a simulação.
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section className="rounded-xl bg-white p-6 shadow-md">
            <h2 className="mb-4 text-lg font-semibold text-[#0B2545]">Demonstrativo de Resultado</h2>
            <table className="w-full border-collapse">
              <tbody>
                <LinhaDemonstrativo label="Receita Bruta" valor={demonstrativo!.receitaBruta} />
                <LinhaDemonstrativo label="Custo de Pessoal (CLT)" valor={-demonstrativo!.custoPessoalClt} />
                <LinhaDemonstrativo label="Custo de CMV" valor={-demonstrativo!.custoCmv} />
                <LinhaDemonstrativo label="Imposto Pago" valor={-demonstrativo!.impostoPago} />
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-[#0B2545]">
                  <td className="py-2 text-sm font-bold text-[#0B2545]">Resultado do Período</td>
                  <td
                    className={`py-2 text-right text-sm font-bold ${
                      resultadoPeriodo >= 0 ? "text-emerald-600" : "text-red-600"
                    }`}
                  >
                    {formatarReais(resultadoPeriodo)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </section>

          <section className="rounded-xl bg-white p-6 shadow-md">
            <h2 className="mb-4 text-lg font-semibold text-[#0B2545]">Evolução do Caixa</h2>
            <EvolucaoCaixaChart historicoCaixa={historicoCaixa} />
          </section>
        </div>
      )}

      {evento && modalAberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg overflow-hidden rounded-xl border-2 border-[#C5A059] bg-white shadow-2xl">
            <div className="flex items-center justify-between bg-[#0B2545] px-6 py-4">
              <h3 className="text-lg font-bold uppercase tracking-wide text-[#C5A059]">
                {evento.titulo}
              </h3>
              <button
                onClick={() => setModalAberto(false)}
                aria-label="Fechar alerta"
                className="text-xl leading-none text-white/70 hover:text-white"
              >
                ×
              </button>
            </div>
            <div className="space-y-4 px-6 py-5">
              <p className="text-sm leading-relaxed text-slate-700">{evento.narrativa}</p>
              {consequenciasEvento.length > 0 && (
                <div>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Consequências
                  </h4>
                  <ul className="space-y-1">
                    {consequenciasEvento.map(([chave, valor]) => (
                      <li
                        key={chave}
                        className="flex justify-between border-b border-slate-100 pb-1 text-sm"
                      >
                        <span className="text-slate-500">{chave}</span>
                        <span className="font-medium text-[#0B2545]">{String(valor)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            <div className="flex justify-end bg-slate-50 px-6 py-3">
              <button
                onClick={() => setModalAberto(false)}
                className="rounded-lg bg-[#0B2545] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0B2545]/90"
              >
                Entendi
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
