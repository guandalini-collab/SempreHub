import React, { useCallback, useEffect, useRef, useState } from "react";

import { api, baixarArquivo } from "../../api";
import EquipeEmpresa from "../../componentes/EquipeEmpresa";
import { PainelOperacional, RelatorioFinanceiro } from "../../componentes/SimulacaoAvancada";
import RelatorioPedagogico from "../../componentes/RelatorioPedagogico";
import {
  Aviso,
  Botao,
  CORES_SERIES,
  Campo,
  Carregando,
  Cartao,
  GraficoLinhas,
  Indicador,
  Modal,
  SeloFase,
  TabelaDre,
  estiloEntrada,
} from "../../componentes/ui";
import { NOME_DORNELAS, NOME_GEM, NOME_REGIME, inteiro, percentual, reais } from "../../formatos";
import type { Decisao, DetalheTurma, Empresa, Equipe, OpcaoEvento, Parametros, Resultado } from "../../tipos";
import type { ModoJogo } from "../../tiposSimulacao";
import { BotaoRedefinirSenha } from "./AlunosTeste";
import { EditorParametros } from "./Parametros";

const INTERVALO_ATUALIZACAO_MS = 15000;

export default function PainelTurma({ turmaId }: { turmaId: number }) {
  const [dados, setDados] = useState<DetalheTurma | null>(null);
  const [eventos, setEventos] = useState<OpcaoEvento[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [empresaAberta, setEmpresaAberta] = useState<number | null>(null);
  const [editandoParametros, setEditandoParametros] = useState(false);
  const sequenciaCarga = useRef(0);
  const [historicos, setHistoricos] = useState<Record<number, Resultado[]>>({});

  const carregar = useCallback(async () => {
    const sequencia = ++sequenciaCarga.current;
    try {
      const detalhe = await api.get<DetalheTurma>(`/api/professor/turmas/${turmaId}`);
      if (sequencia !== sequenciaCarga.current) return;
      setDados(detalhe);
      setErro(null);
    } catch (e) {
      if (sequencia !== sequenciaCarga.current) return;
      setErro(e instanceof Error ? e.message : "Erro ao carregar.");
    }
  }, [turmaId]);

  useEffect(() => {
    setDados(null);
    setEmpresaAberta(null);
    setHistoricos({});
    carregar();
    api.get<OpcaoEvento[]>("/api/professor/eventos").then(setEventos).catch(() => undefined);
    const intervalo = window.setInterval(carregar, INTERVALO_ATUALIZACAO_MS);
    return () => { window.clearInterval(intervalo); sequenciaCarga.current += 1; };
  }, [carregar]);

  // Históricos de caixa de todas as empresas para o gráfico comparativo
  const rodadasJogadas = dados ? dados.turma.rodada_atual - 1 : 0;
  useEffect(() => {
    if (!dados || rodadasJogadas === 0) return;
    Promise.all(
      dados.empresas.map((e) =>
        api
          .get<{ resultados: Resultado[] }>(`/api/professor/turmas/${turmaId}/empresas/${e.id}`)
          .then((r) => [e.id, r.resultados] as const)
      )
    )
      .then((pares) => setHistoricos(Object.fromEntries(pares)))
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [turmaId, rodadasJogadas, dados?.empresas.length]);

  if (erro && !dados) return <Aviso>{erro}</Aviso>;
  if (!dados) return <Carregando />;

  const { turma, empresas, ranking, mercado } = dados;
  const enviadas = empresas.filter((e) => e.decisao_enviada).length;
  const aberta = turma.status === "ABERTA";
  const rotulos = Array.from({ length: rodadasJogadas }, (_, i) => `M${i + 1}`);

  return (
    <div className="space-y-6">
      <div className="rounded-xl bg-marinho p-5 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-ouro">Turma</p>
            <h1 className="text-2xl font-bold">{turma.nome}</h1>
            <p className="mt-1 text-xs text-white/70">{turma.modo_equipe ? "Equipes de 3 a 5 alunos · confirmação de todos os integrantes" : "Participação individual"} · {turma.modo_jogo === "STARTUP" ? "Startup" : turma.modo_jogo === "TRADICIONAL" ? "Empresa tradicional" : "Modelo básico"}{turma.cenario === "CRISE" ? " · recuperação de empresa" : ""}</p>
          </div>
          <div className="text-right">
            <p className="text-xs uppercase tracking-wide text-white/60">Código para os alunos</p>
            <p className="font-mono text-3xl tracking-[0.3em] text-ouro">{turma.codigo}</p>
          </div>
        </div>
        <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Indicador rotulo="Rodada" valor={aberta ? `${turma.rodada_atual} de ${turma.total_rodadas}` : "Encerrada"} destaque />
          <Indicador rotulo="Empresas" valor={empresas.length} />
          <Indicador rotulo={turma.modo_equipe ? "Equipes prontas" : "Decisões enviadas"} valor={aberta ? `${enviadas} de ${empresas.length}` : "—"} />
          <Indicador rotulo="Juros atuais" valor={`${percentual(turma.parametros!.taxa_juros_mensal, 2)} a.m.`} />
        </div>
        {(turma.greve_rodadas_restantes ?? 0) > 0 && (
          <p className="mt-4 rounded-lg bg-white/10 px-3 py-2 text-sm">
            Greve na logística em curso: CMV 40% mais caro por mais {turma.greve_rodadas_restantes} rodada(s).
          </p>
        )}
      </div>

      {erro && <Aviso>{erro}</Aviso>}

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="space-y-6 lg:col-span-2">
          {aberta ? (
            <FecharRodada turmaId={turma.id} rodada={turma.rodada_atual} modoEquipe={turma.modo_equipe} eventos={eventos} empresas={empresas} aoFechar={carregar} />
          ) : (
            <Cartao titulo="Simulação encerrada">
              <p className="text-sm text-slate-600">
                Todas as rodadas foram jogadas. Para estender a simulação, aumente o total de rodadas nos parâmetros.
              </p>
            </Cartao>
          )}
          <Cartao
            titulo="Parâmetros e dados"
            acao={
              <div className="flex gap-2">
                <Botao variante="secundario" onClick={() => setEditandoParametros(true)}>
                  Parâmetros
                </Botao>
                <Botao
                  variante="secundario"
                  disabled={rodadasJogadas === 0}
                  onClick={() => baixarArquivo(`/api/professor/turmas/${turma.id}/exportar.csv`, `semprehub_${turma.codigo}.csv`)}
                >
                  Exportar CSV
                </Botao>
              </div>
            }
          >
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <Dado rotulo="Caixa inicial" valor={reais(turma.parametros!.caixa_inicial)} />
              <Dado rotulo="Preço de referência" valor={reais(turma.parametros!.preco_referencia)} />
              <Dado rotulo="Custo unitário" valor={reais(turma.parametros!.custo_unitario)} />
              <Dado rotulo="Demanda base/empresa" valor={`${inteiro(turma.parametros!.demanda_base_por_empresa)} un.`} />
              <Dado rotulo="Salário-base" valor={reais(turma.parametros!.salario_base)} />
              <Dado rotulo="Custos fixos" valor={reais(turma.parametros!.custos_fixos_mensais)} />
            </dl>
            <p className="mt-3 text-xs text-slate-500">O CSV traz todas as rodadas de todas as empresas, pronto para Excel ou análise estatística.</p>
          </Cartao>
        </div>

        <Cartao titulo={turma.modo_jogo === "LEGADO" ? "Ranking (patrimônio = caixa − dívida)" : "Ranking por patrimônio"} className="lg:col-span-3">
          {empresas.length === 0 ? (
            <p className="text-sm text-slate-500">
              Nenhum aluno entrou ainda. Divulgue o código <strong className="font-mono">{turma.codigo}</strong>.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-slate-500">
                    <th className="pb-2">#</th>
                    <th className="pb-2">Empresa</th>
                    <th className="pb-2 text-right">Patrimônio</th>
                    <th className="pb-2 text-right">Lucro acum.</th>
                    <th className="pb-2 text-right">Mercado</th>
                    <th className="pb-2">Fase</th>
                    {aberta && <th className="pb-2 text-center">Decisão</th>}
                  </tr>
                </thead>
                <tbody>
                  {ranking.map((linha) => {
                    const empresa = empresas.find((e) => e.id === linha.empresa_id)!;
                    return (
                      <tr
                        key={linha.empresa_id}
                        onClick={() => setEmpresaAberta(linha.empresa_id)}
                        className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
                      >
                        <td className="py-2 font-semibold text-ouro">{linha.posicao}º</td>
                        <td className="py-2">
                          <p className="font-medium text-marinho">{linha.empresa}</p>
                          <p className="text-xs text-slate-500">{turma.modo_equipe ? empresa.equipe_membros?.map((m) => m.nome).join(", ") || linha.aluno : linha.aluno}</p>
                        </td>
                        <td className={`py-2 text-right font-semibold ${linha.patrimonio < 0 ? "text-red-700" : "text-marinho"}`}>
                          {reais(linha.patrimonio)}
                        </td>
                        <td className="py-2 text-right">{reais(linha.lucro_acumulado)}</td>
                        <td className="py-2 text-right">{percentual(linha.participacao_mercado)}</td>
                        <td className="py-2">
                          <SeloFase fase={linha.fase} />
                        </td>
                        {aberta && (
                          <td className="py-2 text-center">
                            {empresa.decisao_enviada ? (
                              <span className="text-emerald-600" title={turma.modo_equipe ? "Decisão confirmada pela equipe" : "Decisão enviada"}>✔</span>
                            ) : (
                              <span className="text-amber-600" title={empresa.equipe_pendencias?.join("; ") || "Ainda não enviou"}>…</span>
                            )}
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="mt-2 text-xs text-slate-500">Clique numa empresa para ver decisões e resultados.</p>
            </div>
          )}
        </Cartao>
      </div>

      {turma.modo_jogo !== "LEGADO" && <RelatorioPedagogico turmaId={turma.id} rodada={turma.rodada_atual} temResultados={rodadasJogadas > 0} abrirEmpresa={setEmpresaAberta} />}

      {rodadasJogadas > 0 && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Cartao titulo="Caixa por empresa">
            <GraficoLinhas
              rotulosX={rotulos}
              series={empresas
                .filter((e) => historicos[e.id])
                .map((e, i) => ({
                  nome: e.nome,
                  cor: CORES_SERIES[i % CORES_SERIES.length],
                  valores: historicos[e.id].map((r) => r.caixa_final),
                }))}
            />
          </Cartao>
          <Cartao titulo="Mercado da turma">
            <GraficoLinhas
              rotulosX={mercado.map((m) => `M${m.rodada}`)}
              series={[
                { nome: "Receita total", cor: "#0B2545", valores: mercado.map((m) => m.receita) },
                { nome: "Lucro total", cor: "#C5A059", valores: mercado.map((m) => m.lucro) },
              ]}
            />
            <p className="mt-2 text-xs text-slate-500">
              Preço médio na última rodada: {mercado.length ? reais(mercado[mercado.length - 1].preco_medio) : "—"}
            </p>
          </Cartao>
        </div>
      )}

      {dados.eventos.length > 0 && (
        <Cartao titulo="Eventos da turma">
          <ul className="divide-y divide-slate-100 text-sm">
            {[...dados.eventos].reverse().map((e) => (
              <li key={e.rodada} className="py-2">
                <span className="font-semibold text-marinho">Mês {e.rodada}: {e.titulo}.</span>{" "}
                <span className="text-slate-600">{e.narrativa}</span>
              </li>
            ))}
          </ul>
        </Cartao>
      )}

      {empresaAberta !== null && (
        <DetalheEmpresa turmaId={turma.id} empresaId={empresaAberta} modo={turma.modo_jogo} aoFechar={() => setEmpresaAberta(null)} />
      )}

      {editandoParametros && (
        <EditarParametros
          turmaId={turma.id}
          inicial={turma.parametros!}
          somenteRodadas={turma.rodada_atual > 1}
          modoBloqueado={turma.quantidade_empresas > 0}
          aoFechar={() => setEditandoParametros(false)}
          aoSalvar={async () => {
            setEditandoParametros(false);
            await carregar();
          }}
        />
      )}
    </div>
  );
}

function Dado({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{rotulo}</dt>
      <dd className="font-semibold text-marinho">{valor}</dd>
    </div>
  );
}

function FecharRodada({
  turmaId,
  rodada,
  modoEquipe,
  eventos,
  empresas,
  aoFechar,
}: {
  turmaId: number;
  rodada: number;
  modoEquipe: boolean;
  eventos: OpcaoEvento[];
  empresas: Empresa[];
  aoFechar: () => Promise<void>;
}) {
  const [evento, setEvento] = useState("SORTEAR");
  const [confirmando, setConfirmando] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [mensagem, setMensagem] = useState<{ tipo: "erro" | "sucesso"; texto: string } | null>(null);
  const pendentes = empresas.filter((e) => !e.decisao_enviada);

  useEffect(() => {
    setConfirmando(false);
    setMensagem(null);
  }, [turmaId, rodada]);

  async function fechar() {
    if (modoEquipe && pendentes.length) return;
    setCarregando(true);
    setMensagem(null);
    try {
      const resposta = await api.post<{ evento: OpcaoEvento }>(`/api/professor/turmas/${turmaId}/fechar-rodada`, { evento, rodada });
      setMensagem({ tipo: "sucesso", texto: `Mês ${rodada} fechado. Evento: ${resposta.evento.titulo}.` });
      setConfirmando(false);
      await aoFechar();
    } catch (e) {
      setMensagem({ tipo: "erro", texto: e instanceof Error ? e.message : "Erro ao fechar a rodada." });
    } finally {
      setCarregando(false);
    }
  }

  const descricao = eventos.find((e) => e.codigo === evento)?.narrativa;

  return (
    <Cartao titulo={`Fechar o mês ${rodada}`}>
      <div className="space-y-4">
        <Campo rotulo="Evento macroeconômico do mês">
          <select className={estiloEntrada} value={evento} onChange={(e) => setEvento(e.target.value)}>
            <option value="SORTEAR">Sortear (incerteza de Knight)</option>
            <option value="NENHUM">Nenhum evento</option>
            {eventos.map((e) => (
              <option key={e.codigo} value={e.codigo}>
                {e.titulo}
              </option>
            ))}
          </select>
        </Campo>
        {descricao && <p className="text-xs leading-relaxed text-slate-500">{descricao}</p>}
        {pendentes.length > 0 && (
          <Aviso tipo="info">
            {modoEquipe ? <>
              <p className="font-semibold">{pendentes.length} equipe(s) ainda precisam concluir a decisão. A rodada estará disponível quando todas estiverem prontas.</p>
              <ul className="mt-2 space-y-2">{pendentes.map((e) => <li key={e.id}><strong>{e.nome}:</strong> {(e.equipe_pendencias?.length ? e.equipe_pendencias : ["Decisão ainda não confirmada por todos"]).join("; ")}.</li>)}</ul>
            </> : <>{pendentes.length} empresa(s) ainda não enviaram decisões ({pendentes.map((e) => e.nome).join(", ")}). Se você fechar agora, o sistema repetirá as decisões anteriores delas.</>}
          </Aviso>
        )}
        {mensagem && <Aviso tipo={mensagem.tipo}>{mensagem.texto}</Aviso>}
        {confirmando ? (
          <div className="flex flex-wrap items-center justify-end gap-2">
            <span className="text-sm text-slate-600">Fechar o mês {rodada}? Não é possível desfazer.</span>
            <Botao variante="secundario" onClick={() => setConfirmando(false)}>
              Voltar
            </Botao>
            <Botao carregando={carregando} disabled={modoEquipe && pendentes.length > 0} onClick={fechar}>
              Confirmar
            </Botao>
          </div>
        ) : (
          <div className="flex justify-end">
            <Botao disabled={empresas.length === 0 || (modoEquipe && pendentes.length > 0)} onClick={() => setConfirmando(true)}>
              Fechar rodada
            </Botao>
          </div>
        )}
      </div>
    </Cartao>
  );
}

function DetalheEmpresa({ turmaId, empresaId, modo, aoFechar }: { turmaId: number; empresaId: number; modo: ModoJogo; aoFechar: () => void }) {
  const [dados, setDados] = useState<{ empresa: Empresa; resultados: Resultado[]; decisoes: Decisao[]; equipe?: Equipe | null } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [rodadaSelecionada, setRodadaSelecionada] = useState<number | null>(null);

  useEffect(() => {
    api
      .get<{ empresa: Empresa; resultados: Resultado[]; decisoes: Decisao[]; equipe?: Equipe | null }>(`/api/professor/turmas/${turmaId}/empresas/${empresaId}`)
      .then((d) => {
        setDados(d);
        if (d.resultados.length) setRodadaSelecionada(d.resultados[d.resultados.length - 1].rodada);
      }).catch((e) => setErro(e instanceof Error ? e.message : "Não foi possível carregar esta empresa."));
  }, [turmaId, empresaId]);

  const resultado = dados?.resultados.find((r) => r.rodada === rodadaSelecionada);
  const decisao = dados?.decisoes.find((d) => d.rodada === rodadaSelecionada);

  return (
    <Modal titulo={dados ? dados.empresa.nome : "Empresa"} aoFechar={aoFechar}>
      {erro ? <Aviso>{erro}</Aviso> : !dados ? (
        <Carregando />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
            <span>{dados.empresa.aluno} · {dados.empresa.aluno_email}</span>
            <SeloFase fase={dados.empresa.fase_atual} />
          </div>
          {dados.equipe ? <>
            <EquipeEmpresa empresaId={dados.empresa.id} equipe={dados.equipe} />
            <div className="space-y-2">{dados.equipe.membros.map((m) => <div key={m.aluno_id} className="flex flex-wrap items-center justify-between gap-2"><span className="text-sm text-slate-600">{m.nome}</span><BotaoRedefinirSenha alunoId={m.aluno_id} nome={m.nome} /></div>)}</div>
          </> : <BotaoRedefinirSenha alunoId={dados.empresa.aluno_id} nome={dados.empresa.aluno ?? "o aluno"} />}
          <div className="grid grid-cols-2 gap-3 rounded-lg bg-slate-50 p-3 text-sm sm:grid-cols-4">
            <Dado rotulo="Perfil" valor={`${NOME_GEM[dados.empresa.tipo_entrada_gem]}`} />
            <Dado rotulo="Tipo" valor={NOME_DORNELAS[dados.empresa.classe_dornelas]} />
            <Dado rotulo="Regime" valor={NOME_REGIME[dados.empresa.regime_tributario]} />
            <Dado rotulo="Funcionários" valor={String(dados.empresa.funcionarios)} />
            <Dado rotulo="Caixa" valor={reais(dados.empresa.caixa)} />
            <Dado rotulo="Dívida" valor={reais(dados.empresa.divida)} />
            <Dado rotulo="Autoeficácia" valor={dados.empresa.autoeficacia.toFixed(0)} />
            <Dado rotulo="Networking" valor={dados.empresa.networking.toFixed(0)} />
          </div>
          {dados.empresa.estado_simulacao && <PainelOperacional estado={dados.empresa.estado_simulacao} modo={modo} />}
          {dados.resultados.length === 0 ? (
            <p className="text-sm text-slate-500">A empresa ainda não tem rodadas fechadas.</p>
          ) : (
            <>
              <div className="flex flex-wrap gap-1">
                {dados.resultados.map((r) => (
                  <button
                    key={r.rodada}
                    onClick={() => setRodadaSelecionada(r.rodada)}
                    className={`rounded-md px-2.5 py-1 text-xs font-semibold ${
                      r.rodada === rodadaSelecionada ? "bg-marinho text-white" : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    M{r.rodada}
                  </button>
                ))}
              </div>
              {resultado && (
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">Decisões</p>
                    {decisao ? (
                      <dl className="grid grid-cols-2 gap-2 text-sm">
                        <Dado rotulo="Preço" valor={reais(decisao.preco)} />
                        <Dado rotulo="Marketing" valor={reais(decisao.marketing)} />
                        <Dado rotulo="P&D" valor={reais(decisao.pd)} />
                        <Dado rotulo="Networking" valor={reais(decisao.networking)} />
                        <Dado rotulo="Contratou / demitiu" valor={`${decisao.contratar} / ${decisao.demitir}`} />
                        <Dado rotulo="Empréstimo / amortização" valor={`${reais(decisao.emprestimo)} / ${reais(decisao.amortizacao)}`} />
                      </dl>
                    ) : (
                      <p className="text-sm text-slate-500">—</p>
                    )}
                    {decisao?.automatica && (
                      <p className="mt-2 text-xs text-amber-700">Decisão repetida automaticamente (o aluno não enviou).</p>
                    )}
                    <p className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-slate-600">Mercado</p>
                    <dl className="grid grid-cols-2 gap-2 text-sm">
                      <Dado rotulo="Vendidas / capacidade" valor={`${inteiro(resultado.unidades_vendidas)} / ${inteiro(resultado.capacidade)}`} />
                      <Dado rotulo="Participação" valor={percentual(resultado.participacao_mercado)} />
                    </dl>
                  </div>
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">Demonstrativo</p>
                    <TabelaDre dre={resultado.dre} />
                  </div>
                  {resultado.alertas.length > 0 && (
                    <ul className="space-y-1 md:col-span-2">
                      {resultado.alertas.map((a) => (
                        <li key={a} className="rounded-md border-l-4 border-ouro bg-amber-50 px-3 py-1.5 text-xs text-slate-700">
                          {a}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
              {resultado?.detalhes_simulacao && <RelatorioFinanceiro detalhes={resultado.detalhes_simulacao} />}
            </>
          )}
        </div>
      )}
    </Modal>
  );
}

function EditarParametros({
  turmaId,
  inicial,
  somenteRodadas,
  modoBloqueado,
  aoFechar,
  aoSalvar,
}: {
  turmaId: number;
  inicial: Parametros;
  somenteRodadas: boolean;
  modoBloqueado: boolean;
  aoFechar: () => void;
  aoSalvar: () => Promise<void>;
}) {
  const [valores, setValores] = useState<Parametros>(inicial);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function salvar() {
    setCarregando(true);
    setErro(null);
    try {
      await api.put(`/api/professor/turmas/${turmaId}/parametros`, valores);
      await aoSalvar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao salvar.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <Modal
      titulo="Parâmetros da turma"
      aoFechar={aoFechar}
      rodape={
        <>
          <Botao variante="secundario" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao carregando={carregando} onClick={salvar}>
            Salvar
          </Botao>
        </>
      }
    >
      <EditorParametros valores={valores} aoMudar={setValores} somenteRodadas={somenteRodadas} modoBloqueado={modoBloqueado} />
      {erro && (
        <div className="mt-4">
          <Aviso>{erro}</Aviso>
        </div>
      )}
    </Modal>
  );
}
