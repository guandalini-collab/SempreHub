import { CONFIGURACAO_MOTOR_PADRAO } from "../../tiposSimulacao";
import FormacaoTurma from "../../componentes/FormacaoTurma";
import DiagnosticosEmpresa from "../../componentes/DiagnosticosEmpresa";
import ResultadoProdutos from "../../componentes/ResultadoProdutos";
import ManualMidias from "../../componentes/ManualMidias";
import { ResumoAnalises } from "../../componentes/FerramentasEstrategicas";
import { Conquistas, type Jornada } from "../../componentes/Experiencia";
import LayoutPainel, { SecaoPainel } from "../../componentes/LayoutPainel";
import { GestaoMercado, RelatoriosEmpresariaisProfessor } from "../../componentes/MercadoReal";
import CompetitividadeMercado from "../../componentes/CompetitividadeMercado";
import React, { useCallback, useEffect, useRef, useState } from "react";

import { api, baixarArquivo } from "../../api";
import { BibliotecaAprendizagem } from "../../componentes/Aprendizagem";
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

const ITENS_PAINEL = [
  { id: "visao", titulo: "1. Dados e ingresso", descricao: "Confira o nome da turma e libere seu ingresso para os alunos.", simbolo: "", grupo: "Preparar turma" },
  { id: "configuracao", titulo: "2. Configurar simulação", descricao: "Revise os parâmetros antes de orientar os alunos.", simbolo: "", grupo: "Preparar turma" },
  { id: "equipes", titulo: "3. Conferir participantes", descricao: "Confira alunos, empresas e pendências de envio.", simbolo: "", grupo: "Preparar turma" },
  { id: "mercado", titulo: "4. Preparar rodada", descricao: "Pesquise, revise e publique notícias e produtos para os alunos.", simbolo: "", grupo: "Conduzir rodada" },
  { id: "rodada", titulo: "5. Acompanhar envios", descricao: "Acompanhe as decisões e veja o que falta para encerrar a rodada.", simbolo: "", grupo: "Conduzir rodada" },
  { id: "fechamento", titulo: "6. Encerrar rodada", descricao: "Confira os envios e confirme o encerramento. O sistema sorteia os eventos e calcula os resultados.", simbolo: "", grupo: "Conduzir rodada" },
  { id: "resultados", titulo: "7. Consultar resultados", descricao: "Analise os resultados. Para a próxima rodada, retome a etapa 4 no menu lateral.", simbolo: "", grupo: "Consultar resultados" },
  { id: "aprendizagem", titulo: "Autores e referências", descricao: "Consulte as referências para orientar a atividade.", simbolo: "", grupo: "Apoio" },
  { id: "analises", titulo: "Ferramentas de análise", descricao: "Consulte os conceitos e as ferramentas para orientar os alunos.", simbolo: "", grupo: "Apoio" },
  { id: "midias", titulo: "Guia de campanhas", descricao: "Consulte os formatos, objetivos e custos das campanhas.", simbolo: "", grupo: "Apoio" },
];

const INTERVALO_ATUALIZACAO_MS = 15000;

export default function PainelTurma({ turmaId }: { turmaId: number }) {
  const [dados, setDados] = useState<DetalheTurma | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [empresaAberta, setEmpresaAberta] = useState<number | null>(null);
  const [editandoParametros, setEditandoParametros] = useState(false);
  const [secao, setSecao] = useState("visao");
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
    <LayoutPainel itens={ITENS_PAINEL} ativa={secao} aoSelecionar={setSecao} rodada={turma.rodada_atual} total={turma.total_rodadas} concluidas={aberta ? rodadasJogadas : turma.total_rodadas} perfil="Professor" contexto={{ turma: turma.nome, codigo: turma.codigo, status: aberta ? `${enviadas} de ${empresas.length} empresas enviaram decisões` : "Simulação encerrada" }}>
      <SecaoPainel id="visao" ativa={secao}>
      <FormacaoTurma turma={turma} aoAtualizar={carregar}/>
      <div className="rounded-xl bg-marinho p-5 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-ouro">Turma</p>
            <h1 className="text-2xl font-bold">{turma.nome}</h1>
            <p className="mt-1 text-xs text-white/70">{turma.modo_equipe ? "Equipes de 3 a 5 alunos · envio pelo líder" : "Participação individual"} · {turma.modo_jogo === "STARTUP" ? "Startup" : turma.modo_jogo === "TRADICIONAL" ? "Empresa tradicional" : "Modelo básico"}{turma.cenario === "CRISE" ? " · recuperação de empresa" : ""}</p>
          </div>
          <div className="text-right">
            <p className="text-xs uppercase tracking-wide text-white/60">Ingresso pelo nome da turma</p>
            <p className="text-lg font-bold text-ouro">{turma.visivel_ingresso ? "Disponível" : "Oculta para ingresso"}</p>
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

      <Cartao titulo="Prontidão da turma"><p className="mb-3 text-sm text-slate-600">{enviadas} de {empresas.length} empresas prontas nesta rodada</p><div className="h-3 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label="Empresas com decisões enviadas" aria-valuenow={empresas.length ? Math.round(enviadas / empresas.length * 100) : 0} aria-valuemin={0} aria-valuemax={100}><div className="h-full bg-emerald-500 transition-all" style={{ width: `${empresas.length ? enviadas / empresas.length * 100 : 0}%` }} /></div><p className="mt-3 text-xs text-slate-500">Os envios finais dos líderes atualizam este painel automaticamente.</p></Cartao>

      </SecaoPainel>
      {erro && <Aviso>{erro}</Aviso>}

      <SecaoPainel id="mercado" ativa={secao}>
      <CompetitividadeMercado config={turma.parametros?.configuracao_simulacao ?? CONFIGURACAO_MOTOR_PADRAO} equipes={empresas.length} />
      <GestaoMercado turmaId={turmaId} rodada={dados.turma.rodada_atual} empresas={dados.empresas} />
      </SecaoPainel>
      <SecaoPainel id="midias" ativa={secao}><ManualMidias /></SecaoPainel>
      <SecaoPainel id="aprendizagem" ativa={secao}>
      <BibliotecaAprendizagem mercadoSeparado conteudo="REFERENCIAS" rodada={turma.rodada_atual} modo={turma.modo_jogo} />

      </SecaoPainel>
      <SecaoPainel id="analises" ativa={secao}><BibliotecaAprendizagem mercadoSeparado conteudo="ANALISES" rodada={turma.rodada_atual} modo={turma.modo_jogo} /></SecaoPainel>
      <SecaoPainel id="rodada" ativa={secao}>
      <Cartao titulo="Situação da rodada">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg bg-slate-50 p-4"><p className="text-sm text-slate-600">Empresas</p><p className="text-2xl font-bold">{empresas.length}</p></div>
          <div className="rounded-lg bg-emerald-50 p-4"><p className="text-sm text-emerald-800">Decisões prontas</p><p className="text-2xl font-bold">{aberta ? enviadas : "—"}</p></div>
          <div className="rounded-lg bg-amber-50 p-4"><p className="text-sm text-amber-900">Envios pendentes</p><p className="text-2xl font-bold">{aberta ? empresas.length - enviadas : "—"}</p></div>
        </div>
        <div className="mt-5 border-t border-slate-200 pt-4">
          <h3 className="font-semibold">O que fazer agora</h3>
          <p className="mt-2 text-sm text-slate-600">{!aberta ? "A simulação terminou. Consulte os resultados das empresas." : empresas.length === 0 ? "Compartilhe o código de entrada para os alunos participarem da turma." : enviadas < empresas.length ? "Confira as empresas com envio pendente antes de encerrar a rodada." : "Todos os envios estão prontos. Encerre a rodada para calcular os resultados."}</p>

          <p className="mt-3 text-xs text-slate-500">Continue pelo menu lateral: etapa 3 para conferir participantes e pendências; etapa 6 quando estiver pronto para encerrar. Os resultados só são calculados após confirmar o encerramento.</p>
        </div>
      </Cartao>
      </SecaoPainel>
      <SecaoPainel id="fechamento" ativa={secao}>
          {aberta ? (
            <FecharRodada turmaId={turma.id} rodada={turma.rodada_atual} modoEquipe={turma.modo_equipe} empresas={empresas} aoFechar={carregar} />
          ) : (
            <Cartao titulo="Simulação encerrada">
              <p className="text-sm text-slate-600">
                Todas as rodadas foram jogadas. Para estender a simulação, aumente o total de rodadas nos parâmetros.
              </p>
            </Cartao>
          )}
      </SecaoPainel>
      <SecaoPainel id="configuracao" ativa={secao}>
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
      </SecaoPainel>
      <SecaoPainel id="equipes" ativa={secao}>
        <Cartao titulo="Envios e empresas da turma" className="lg:col-span-3">
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
                          <button type="button" className="font-medium text-marinho underline decoration-ouro underline-offset-4" onClick={(e) => { e.stopPropagation(); setEmpresaAberta(linha.empresa_id); }}>{linha.empresa}</button>
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
                              <span className="text-emerald-600" title={turma.modo_equipe ? "Decisão confirmada pela equipe" : "Decisão enviada"}>{turma.modo_equipe ? "Confirmada" : "Enviada"}</span>
                            ) : (
                              <span className="text-amber-800">Pendente{empresa.equipe_pendencias?.length ? <span className="mt-1 block text-xs">{empresa.equipe_pendencias.join("; ")}</span> : null}</span>
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
      </SecaoPainel>
      <SecaoPainel id="resultados" ativa={secao}>
      <RelatoriosEmpresariaisProfessor turmaId={turmaId} ultimaRodada={rodadasJogadas} empresas={empresas} />
      {rodadasJogadas === 0 && <Cartao titulo="Resultados ainda indisponíveis"><p>Os gráficos e indicadores serão disponibilizados após o encerramento da primeira rodada. As empresas podem ser acompanhadas em Alunos e empresas.</p></Cartao>}
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
                { nome: "Receita total", cor: "#102A68", valores: mercado.map((m) => m.receita) },
                { nome: "Lucro total", cor: "#FFC233", valores: mercado.map((m) => m.lucro) },
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

      </SecaoPainel>
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
    </LayoutPainel>
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
  empresas,
  aoFechar,
}: {
  turmaId: number;
  rodada: number;
  modoEquipe: boolean;
  empresas: Empresa[];
  aoFechar: () => Promise<void>;
}) {
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
      const resposta = await api.post<{ evento: OpcaoEvento }>(`/api/professor/turmas/${turmaId}/fechar-rodada`, { evento: "SORTEAR", rodada });
      setMensagem({ tipo: "sucesso", texto: `Mês ${rodada} fechado. Evento: ${resposta.evento.titulo}.` });
      setConfirmando(false);
      await aoFechar();
    } catch (e) {
      setMensagem({ tipo: "erro", texto: e instanceof Error ? e.message : "Erro ao fechar a rodada." });
    } finally {
      setCarregando(false);
    }
  }


  return (
    <Cartao titulo={`Fechar o mês ${rodada}`}>
      <div className="space-y-4">
        <p className="rounded-lg bg-blue-50 p-4 text-sm">Os eventos são sorteados automaticamente ao encerrar a rodada. Podem ocorrer de um a três eventos, com aumentos ou reduções de demanda, juros e outros efeitos. Todos atingem a mesma turma. Também pode haver uma rodada sem eventos, conforme a probabilidade configurada.</p>
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
  const [dados, setDados] = useState<{ empresa: Empresa; resultados: Resultado[]; decisoes: Decisao[]; jornada?: Jornada; equipe?: Equipe | null } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [rodadaSelecionada, setRodadaSelecionada] = useState<number | null>(null);

  useEffect(() => {
    api
      .get<{ empresa: Empresa; resultados: Resultado[]; decisoes: Decisao[]; jornada?: Jornada; equipe?: Equipe | null }>(`/api/professor/turmas/${turmaId}/empresas/${empresaId}`)
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
          <details className="rounded-xl border p-3"><summary className="cursor-pointer font-semibold">Conquistas e evolução desta empresa</summary><div className="mt-3"><Conquistas jornada={dados.jornada} /></div></details>
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
          <DiagnosticosEmpresa turmaId={turmaId} empresaId={empresaId}/>
          {dados.decisoes.filter(d => d.plano_comercial?.analises).map(d => <ResumoAnalises key={d.rodada} rodada={d.rodada} valor={d.plano_comercial!.analises!} />)}
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
                    {decisao?.simulacao?.centro_gravidade && <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-3"><h4 className="font-bold">Estudo de centro de gravidade</h4><p className="mt-2 text-sm">Local escolhido: X {decisao.simulacao.centro_gravidade.local_x ?? "não informado"} km · Y {decisao.simulacao.centro_gravidade.local_y ?? "não informado"} km</p><p className="mt-1 whitespace-pre-wrap text-sm">{decisao.simulacao.centro_gravidade.justificativa || "Sem justificativa registrada."}</p><ul className="mt-2 text-xs">{decisao.simulacao.centro_gravidade.pontos.map((p, i) => <li key={i}>{p.nome || `Local ${i + 1}`}: X {p.x}, Y {p.y}, volume {p.volume}</li>)}</ul></div>}
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
              {resultado && !resultado.detalhes_simulacao && <ResultadoProdutos produtos={resultado.produtos_resultado??[]}/>}
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
