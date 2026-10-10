import IndicadoresDepartamentais, { AREAS_INDICADORES } from "../../componentes/IndicadoresDepartamentais";
import CentralManuais from "../../componentes/CentralManuais";
import ResultadoProdutos from "../../componentes/ResultadoProdutos";
import ManualMidias from "../../componentes/ManualMidias";
import { ControleVisual, ResumoNegocio, Conquistas, FeedResultados, ViradaRodada } from "../../componentes/Experiencia";
import LayoutPainel, { SecaoPainel } from "../../componentes/LayoutPainel";
import { EditorMix, MercadoPublicado } from "../../componentes/MercadoReal";
import CompetitividadeMercado from "../../componentes/CompetitividadeMercado";
import React, { useCallback, useEffect, useRef, useState } from "react";

import { api, ErroApi } from "../../api";
import { BibliotecaAprendizagem } from "../../componentes/Aprendizagem";
import { RelatorioPrimeiraRodada } from "../../componentes/ConteudoRodada";
import EquipeEmpresa from "../../componentes/EquipeEmpresa";
import { ControlesSimulacao, PainelOperacional, PreviaOperacional, RelatorioFinanceiro } from "../../componentes/SimulacaoAvancada";
import {
  RevisaoCampos,
  Aviso,
  BarraProgresso,
  Botao,
  Campo,
  Carregando,
  Cartao,
  EntradaNumero,
  GraficoLinhas,
  Indicador,
  Modal,
  SeloFase,
  TabelaDre,
  estiloEntrada,
} from "../../componentes/ui";
import { NOME_DORNELAS, NOME_GEM, NOME_REGIME, inteiro, percentual, reais, umDecimal } from "../../formatos";
import type { Decisao, DecisaoEntrada, EventoRodada, PainelAluno, PrevisaoDecisao, RegimeTributario } from "../../tipos";
import { CONFIGURACAO_MOTOR_PADRAO, DECISAO_SIMULACAO_PADRAO } from "../../tiposSimulacao";
import type { DecisaoSimulacao } from "../../tiposSimulacao";

const FERRAMENTAS = ["SWOT", "PORTER", "BCG", "PESTEL", "SEGMENTACAO"];
const ANALISES_APRENDIZAGEM = ["5 Forças de Porter", "PESTEL", "Análise de mercado", "SWOT (FOFA)", "Análise financeira", "Segmentação de mercado"];
const ITENS_PAINEL = [
  {id: "manuais", titulo: "Manuais", descricao: "Consulte ou baixe os manuais em PDF.", simbolo: "", grupo: "Manuais"},
  {
    "id": "visao",
    "titulo": "Visão Geral / Mesa do CEO",
    "descricao": "Resumo do seu negócio.",
    "simbolo": "◈",
    "grupo": "Minha empresa"
  },
  {
    "id": "rodada",
    "titulo": "O que fazer nesta rodada",
    "descricao": "Veja o que fazer e o que falta enviar.",
    "simbolo": "▷",
    "grupo": "Rodada atual"
  },
  {
    "id": "equipe",
    "titulo": "Minha empresa e equipe",
    "descricao": "Integrantes e informações da empresa.",
    "simbolo": "♙",
    "grupo": "Minha empresa"
  },
  {
    "id": "mercado",
    "titulo": "Notícias e mercado",
    "descricao": "Leia antes de tomar suas decisões.",
    "simbolo": "▤",
    "grupo": "Rodada atual"
  },
  { "id": "midias", "titulo": "Manual de mídias", "descricao": "Formatos, objetivos e custos das campanhas.", "simbolo": "◉", "grupo": "Estratégia e ajuda" },
  {
    "id": "aprendizagem",
    "titulo": "Autores e referências",
    "descricao": "Consulte as referências para apoiar suas decisões.",
    "simbolo": "◇",
    "grupo": "Estratégia e ajuda"
  },
  {id: "analises", titulo: "Ferramentas de análise", descricao: "Selecione uma ferramenta no submenu lateral.", simbolo: "", grupo: "Estratégia e ajuda"},
  ...ANALISES_APRENDIZAGEM.map((titulo, indice) => ({id: `analise-${indice}`, titulo, descricao: "Consulte os conceitos para apoiar suas decisões.", simbolo: "", grupo: "Estratégia e ajuda", pai: "analises"})),
  {
    "id": "decisoes",
    "titulo": "Produtos e marketing",
    "descricao": "Escolha produtos, preços e campanhas.",
    "simbolo": "✎",
    "grupo": "Decisões da rodada"
  },
  {id: "pd", titulo: "P&D", descricao: "Tecnologia e melhoria dos produtos.", simbolo: "", grupo: "Decisões da rodada"},
  {id: "rh", titulo: "RH", descricao: "Funcionários, remuneração e capacitação.", simbolo: "", grupo: "Decisões da rodada"},
  { "id": "estrategia", "titulo": "Ferramentas e segmentação", "descricao": "SWOT, Porter, BCG, PESTEL e público-alvo.", "simbolo": "◇", "grupo": "Decisões da rodada" },
  ...FERRAMENTAS.map(id => ({id: `ferramenta-${id}`, titulo: id === "PORTER" ? "Porter - 5 forças" : id === "SEGMENTACAO" ? "Segmentação do mercado" : id, descricao: "Consulte e registre as escolhas desta ferramenta.", simbolo: "", grupo: "Decisões da rodada", pai: "estrategia"})),
  {
    "id": "financas",
    "titulo": "Finanças",
    "descricao": "Cálculos, crédito, pagamentos e tributos.",
    "simbolo": "$",
    "grupo": "Decisões da rodada"
  },
  {
    "id": "producao",
    "titulo": "Produção",
    "descricao": "Capacidade, equipe e operação.",
    "simbolo": "⚒",
    "grupo": "Decisões da rodada"
  },
  {
    "id": "logistica",
    "titulo": "Logística",
    "descricao": "Frete e entrega dos produtos.",
    "simbolo": "➜",
    "grupo": "Decisões da rodada"
  },
  {
    "id": "resultados",
    "titulo": "Resultados, DRE e balanço",
    "descricao": "Indicadores e demonstrativos financeiros.",
    "simbolo": "▥",
    "grupo": "Resultados e evolução"
  },
  ...AREAS_INDICADORES.map(a => ({id: `resultado-${a.id}`, titulo: a.titulo, descricao: "Consulte os valores da rodada e interprete-os com sua equipe usando o manual.", simbolo: "", grupo: "Resultados e evolução", pai: "resultados"})),
  {id:"demonstrativos",titulo:"DRE e balanço",descricao:"Demonstrativos e resultado do mês.",simbolo:"",grupo:"Resultados e evolução",pai:"resultados"},
  {id:"evolucao",titulo:"Evolução por rodada",descricao:"Compare caixa, lucro e participação ao longo do tempo.",simbolo:"",grupo:"Resultados e evolução",pai:"resultados"},
  {id:"historico",titulo:"Histórico detalhado",descricao:"Consulte as decisões e os resultados anteriores.",simbolo:"",grupo:"Resultados e evolução",pai:"resultados"},
  {
    "id": "relatorios",
    "titulo": "Relatórios da empresa",
    "descricao": "Leia a análise das rodadas concluídas.",
    "simbolo": "▧",
    "grupo": "Resultados e evolução"
  },
  {
    "id": "conquistas",
    "titulo": "Conquistas",
    "descricao": "Sua evolução no jogo.",
    "simbolo": "★",
    "grupo": "Resultados e evolução"
  }
];

const AREA_REVISAO: Record<string,string> = {pd: "decisoes", rh: "producao"};
const AREAS_DECISAO = ["decisoes", "financas", "producao", "logistica"];

const INTERVALO_ATUALIZACAO_MS = 15000;

function chaveEventoVisto(empresaId: number) {
  return `semprehub.evento-visto.${empresaId}`;
}

function lerEventoVisto(empresaId: number): number {
  try {
    return Number(window.localStorage.getItem(chaveEventoVisto(empresaId)) ?? 0);
  } catch {
    return 0;
  }
}

function gravarEventoVisto(empresaId: number, rodada: number) {
  try {
    window.localStorage.setItem(chaveEventoVisto(empresaId), String(rodada));
  } catch {
    /* sem armazenamento: o aviso pode reaparecer ao recarregar */
  }
}

export default function PainelEmpresa({ empresaId }: { empresaId: number }) {
  const [painel, setPainel] = useState<PainelAluno | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [eventoAberto, setEventoAberto] = useState<EventoRodada | null>(null);
  const [secao, setSecao] = useState("rodada");
  const sequenciaCarga = useRef(0);

  const carregar = useCallback(async () => {
    const sequencia = ++sequenciaCarga.current;
    try {
      const dados = await api.get<PainelAluno>(`/api/aluno/empresas/${empresaId}`);
      if (sequencia !== sequenciaCarga.current) return;
      setPainel(dados);
      const ultimoEvento = dados.eventos[dados.eventos.length - 1];
      if (ultimoEvento && ultimoEvento.rodada > lerEventoVisto(empresaId)) {
        setEventoAberto(ultimoEvento);
      }
      setErro(null);
      return dados;
    } catch (e) {
      if (sequencia !== sequenciaCarga.current) return;
      setErro(e instanceof Error ? e.message : "Erro ao carregar.");
    }
  }, [empresaId]);

  useEffect(() => {
    setPainel(null);
    setEventoAberto(null);
    carregar();
    const intervalo = window.setInterval(carregar, INTERVALO_ATUALIZACAO_MS);
    return () => { window.clearInterval(intervalo); sequenciaCarga.current += 1; };
  }, [carregar]);

  if (erro && !painel) return <Aviso>{erro}</Aviso>;
  if (!painel) return <Carregando />;

  const { empresa, turma, resultados } = painel;
  const ultimo = resultados[resultados.length - 1];
  const encerrada = turma.status === "ENCERRADA";

  function fecharEvento() {
    if (eventoAberto) gravarEventoVisto(empresaId, eventoAberto.rodada);
    setEventoAberto(null);
  }

  return (
    <LayoutPainel itens={ITENS_PAINEL.map(i => ({...i, ...(["mercado", "decisoes", "financas", "producao", "logistica", "equipe"].includes(i.id) ? {grupo: "Rodada atual", pai: "rodada"} : {}), estado: i.id === "logistica" && turma.modo_jogo !== "TRADICIONAL" ? "Sem decisão neste modelo" : (AREAS_DECISAO.includes(i.id) || ["pd", "rh"].includes(i.id)) ? painel.decisao_atual?.enviada_em ? "Enviada" : painel.decisao_atual?.revisao_areas?.[(AREA_REVISAO[i.id] || i.id) as keyof NonNullable<DecisaoEntrada["revisao_areas"]>] ? "Rascunho salvo · conferido" : "Decisão pendente" : undefined}))} ativa={secao} aoSelecionar={setSecao} rodada={turma.rodada_atual} total={turma.total_rodadas} concluidas={resultados.length} perfil="Aluno" contexto={{ turma: turma.nome, empresa: empresa.nome, caixa: empresa.caixa, alertas: painel.pendencias_envio?.length ?? 0, status: encerrada ? "Simulação encerrada" : painel.decisao_atual?.enviada_em ? "Decisão enviada · acompanhe a rodada" : "Decisão pendente · prepare e envie" }}>
      <SecaoPainel id="rodada" ativa={secao}>
        <Cartao titulo={encerrada ? "Simulação concluída" : `O que fazer na rodada ${turma.rodada_atual}`}>
          <p className="mb-5 text-sm text-slate-600">{encerrada ? "Consulte os resultados e os relatórios da sua empresa." : painel.decisao_atual?.enviada_em ? "O líder enviou a decisão. Acompanhe os resultados quando a rodada encerrar." : "Siga os passos no menu lateral. Produtos, finanças, produção e logística fazem parte de uma única decisão da rodada."}</p>
          <p className="mb-4 text-sm">Última versão salva: {AREAS_DECISAO.filter(a => a !== "logistica" || turma.modo_jogo === "TRADICIONAL").map(a => `${a === "decisoes" ? "Marketing" : a === "financas" ? "Finanças" : a === "producao" ? "Produção" : "Logística"}: ${painel.decisao_atual?.revisao_areas?.[a as keyof NonNullable<DecisaoEntrada["revisao_areas"]>] ? "revisado" : "revisar"}`).join(" · ")}</p>
          <p className="mt-5 text-sm text-slate-600">Use o submenu “O que fazer nesta rodada”, à esquerda, para abrir cada área.</p>
        </Cartao>
      </SecaoPainel>
      <SecaoPainel id="visao" ativa={secao}>
      <div className="rounded-xl bg-marinho p-5 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-ouro">{turma.nome}</p>
            <h1 className="text-2xl font-bold">{empresa.nome}</h1>
            <p className="mt-1 text-xs text-white/60">
              {NOME_GEM[empresa.tipo_entrada_gem]} · {NOME_DORNELAS[empresa.classe_dornelas]}
            </p>
            {turma.modo_jogo !== "LEGADO" && <p className="mt-1 text-xs text-white/60">{turma.modo_jogo === "STARTUP" ? "Startup digital" : "Empresa tradicional"} · {turma.cenario === "CRISE" ? "Recuperação de empresa em crise" : "Começar do zero"}</p>}
          </div>
          <div className="flex flex-col items-end gap-2">
            <SeloFase fase={empresa.fase_atual} />
            <p className="text-sm text-white/80">
              {encerrada ? "Simulação encerrada" : `Mês ${turma.rodada_atual} de ${turma.total_rodadas}`}
            </p>
          </div>
        </div>

        {empresa.fase_atual === "SOBREVIVENCIA" && (
          <div className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-bold uppercase tracking-wide">
            Alerta: estado de sobrevivência — o caixa não cobre um mês de custos fixos
          </div>
        )}

        <details className="mt-4 border-t border-white/15 pt-3"><summary className="cursor-pointer text-sm text-white/80">Perfil, estrutura e desenvolvimento da empresa</summary>
        <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <Indicador rotulo="Caixa" valor={reais(empresa.caixa)} destaque />
          <Indicador rotulo="Dívida" valor={reais(empresa.divida)} />
          <Indicador rotulo="Patrimônio" valor={reais(empresa.patrimonio)} />
          <Indicador rotulo="Regime" valor={NOME_REGIME[empresa.regime_tributario]} />
          <Indicador rotulo="Funcionários" valor={empresa.funcionarios} />
          <Indicador
            rotulo="Ranking"
            valor={painel.posicao_ranking && resultados.length ? `${painel.posicao_ranking}º de ${painel.total_empresas}` : "—"}
          />
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          <BarraProgresso escuro rotulo="Autoeficácia" valor={empresa.autoeficacia} />
          <BarraProgresso escuro rotulo="Necessidade de realização" valor={empresa.necessidade_realizacao} />
          <BarraProgresso escuro rotulo="Networking" valor={empresa.networking} />
        </div>
        </details>
      </div>

      <section className="rounded-xl border-2 border-ouro bg-amber-50 p-5" aria-label="Ambiente de competição">
        <h2 className="text-lg font-bold text-marinho">Você está em um mercado competitivo</h2>
        <p className="mt-2 text-sm text-slate-700">Sua empresa disputa clientes com {Math.max(0, painel.total_empresas - 1)} outra(s) empresa(s) da turma e {(turma.parametros?.configuracao_simulacao ?? turma.configuracao_simulacao ?? CONFIGURACAO_MOTOR_PADRAO).concorrentes_virtuais} concorrente(s) externo(s) simulados, conforme a configuração do sistema. Preços, produtos, comunicação e capacidade de atendimento influenciam os resultados de cada rodada.</p>
        <p className="mt-2 text-sm font-semibold text-marinho">As decisões das outras empresas também afetam sua participação no mercado.</p>
      </section>
      <ResumoNegocio painel={painel} aoResultados={() => setSecao("resultados")} />
      <Cartao titulo="Sua missão nesta rodada"><ol className="space-y-3 text-sm"><li>1. Consulte as notícias e análises do mercado.</li><li>2. Defina a estratégia e as decisões da sua empresa.</li><li>3. Envie a decisão e acompanhe os resultados.</li></ol><p className="my-4 font-semibold">{encerrada ? "Jornada concluída: confira seu desempenho." : painel.decisao_atual?.enviada_em ? "Decisão registrada. Acompanhe os resultados e o fechamento da rodada." : "Próximo objetivo: preparar e enviar sua decisão."}</p><Botao onClick={() => setSecao(encerrada ? "resultados" : "decisoes")}>{encerrada ? "Analisar resultados" : "Ir para decisões"}</Botao></Cartao>
      </SecaoPainel>
      {erro && <Aviso>{erro}</Aviso>}
      <SecaoPainel id="equipe" ativa={secao}>
      {!turma.modo_equipe && <Cartao titulo="Participação individual"><p>Você administra esta empresa individualmente.</p></Cartao>}
      {turma.modo_equipe && painel.equipe && <EquipeEmpresa empresaId={empresa.id} equipe={painel.equipe} podeEditar={!encerrada && turma.rodada_atual === 1 && painel.equipe.pode_gerenciar} aoSalvar={carregar} rodada={turma.rodada_atual} encerrada={encerrada} />}
      {empresa.estado_simulacao && <PainelOperacional estado={empresa.estado_simulacao} modo={turma.modo_jogo} />}
      </SecaoPainel>
      <SecaoPainel id="conquistas" ativa={secao}><Conquistas jornada={painel.jornada} /></SecaoPainel>
      <SecaoPainel id="mercado" ativa={secao}>
      <CompetitividadeMercado config={turma.parametros?.configuracao_simulacao ?? CONFIGURACAO_MOTOR_PADRAO} equipes={painel.total_empresas} />
      <FeedResultados jornada={painel.jornada} aoResultados={() => setSecao("resultados")} />
      <MercadoPublicado visao="mercado" empresaId={empresa.id} rodada={turma.rodada_atual} />
      </SecaoPainel>
      <SecaoPainel id="manuais" ativa={secao}><CentralManuais perfil="ALUNO" /></SecaoPainel>
      <SecaoPainel id="midias" ativa={secao}><ManualMidias /></SecaoPainel>
      <SecaoPainel id="aprendizagem" ativa={secao}>
      <BibliotecaAprendizagem mercadoSeparado conteudo="REFERENCIAS" rodada={turma.rodada_atual} modo={turma.modo_jogo} empresaId={empresa.id} />
      </SecaoPainel>
      <SecaoPainel id="analises" ativa={secao}><Cartao titulo="Ferramentas de análise"><p>Selecione a ferramenta desejada no submenu lateral para consultar seu conteúdo.</p></Cartao></SecaoPainel>
      {ANALISES_APRENDIZAGEM.map((_, indice) => <SecaoPainel key={indice} id={`analise-${indice}`} ativa={secao}><BibliotecaAprendizagem mercadoSeparado conteudo="ANALISES" ferramenta={indice} rodada={turma.rodada_atual} modo={turma.modo_jogo} empresaId={empresa.id} /></SecaoPainel>)}
      <SecaoPainel id="relatorios" ativa={secao}>
      <MercadoPublicado visao="relatorios" empresaId={empresa.id} rodada={turma.rodada_atual} />
      <RelatorioPrimeiraRodada empresaId={empresa.id} disponivel={resultados.some(r => r.rodada === 1)} />

      </SecaoPainel>
      <SecaoPainel id={(AREAS_DECISAO.includes(secao) || ["pd", "rh"].includes(secao) || secao === "estrategia" || secao.startsWith("ferramenta-")) ? secao : "decisoes"} ativa={secao}>
        <div>
          {encerrada ? (
            <Cartao titulo="Simulação encerrada">
              <p className="text-sm text-slate-600">
                A turma concluiu as {turma.total_rodadas} rodadas. Sua empresa terminou em{" "}
                <strong>
                  {painel.posicao_ranking}º lugar de {painel.total_empresas}
                </strong>{" "}
                no ranking de patrimônio, com {reais(empresa.patrimonio)}.
              </p>
            </Cartao>
          ) : (
            <FormularioDecisao key={empresa.id} painel={painel} area={secao.startsWith("ferramenta-") ? "estrategia" : secao} ferramenta={secao.startsWith("ferramenta-") ? secao.slice(11) : undefined} aoNavegar={setSecao} aoEnviar={carregar} />
          )}
        </div>
      </SecaoPainel>
      <SecaoPainel id="resultados" ativa={secao}><Cartao titulo="Resultados da empresa"><p>Selecione uma área no submenu lateral. Compare os valores e consulte o manual do aluno para interpretar os indicadores antes de decidir a próxima rodada.</p>{ultimo&&<p className="mt-4 font-semibold">Última rodada concluída: {ultimo.rodada} · Caixa: {reais(ultimo.caixa_final)} · Lucro líquido: {reais(ultimo.dre.lucro_liquido)}</p>}</Cartao></SecaoPainel>
      {AREAS_INDICADORES.map(a=><SecaoPainel key={a.id} id={`resultado-${a.id}`} ativa={secao}><IndicadoresDepartamentais area={a.id} resultado={ultimo}/></SecaoPainel>)}
      <SecaoPainel id="demonstrativos" ativa={secao}>
      {ultimo && <IndicadoresFinanceiros resultado={ultimo} />}
        <div className="grid gap-6 xl:grid-cols-2">
          <Cartao titulo={ultimo ? `Resultado do mês ${ultimo.rodada}` : "Resultado do mês"}>
            {ultimo ? (
              <>
                <div className="mb-4 grid grid-cols-3 gap-2 rounded-lg bg-slate-50 p-3 text-center text-xs">
                  <div>
                    <p className="text-slate-500">Vendidas</p>
                    <p className="text-base font-semibold text-marinho">{inteiro(ultimo.unidades_vendidas)}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Capacidade</p>
                    <p className="text-base font-semibold text-marinho">{inteiro(ultimo.capacidade)}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Mercado</p>
                    <p className="text-base font-semibold text-marinho">{percentual(ultimo.participacao_mercado)}</p>
                  </div>
                </div>
                <details className="rounded-xl border border-slate-200 p-4"><summary className="cursor-pointer font-semibold">Ver DRE completa</summary><div className="mt-4"><TabelaDre dre={ultimo.dre} /></div></details>
                <p className="mt-2 text-xs text-slate-500">
                  Alíquota efetiva de tributos: {percentual(ultimo.aliquota_efetiva, 2)} da receita.
                </p>
                {ultimo.alertas.length > 0 && (
                  <ul className="mt-4 space-y-2">
                    {ultimo.alertas.map((alerta) => (
                      <li key={alerta} className="rounded-md border-l-4 border-ouro bg-amber-50 px-3 py-2 text-xs text-slate-700">
                        {alerta}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            ) : (
              <p className="text-sm text-slate-500">
                Nenhuma rodada fechada ainda. Envie suas decisões e aguarde o fechamento do mês pelo sistema.
              </p>
            )}
          </Cartao>
          <Cartao titulo="Mercado no último mês">
            {painel.mercado.length ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-slate-500">
                    <th className="pb-2">Empresa</th>
                    <th className="pb-2 text-right">Preço</th>
                    <th className="pb-2 text-right">Participação</th>
                  </tr>
                </thead>
                <tbody>
                  {painel.mercado.map((linha) => (
                    <tr key={linha.empresa} className={`border-t border-slate-100 ${linha.propria ? "font-semibold text-marinho" : "text-slate-600"}`}>
                      <td className="py-1.5">{linha.empresa}{linha.propria && " (você)"}</td>
                      <td className="py-1.5 text-right">{reais(linha.preco)}</td>
                      <td className="py-1.5 text-right">{percentual(linha.participacao_mercado)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-sm text-slate-500">Os preços dos concorrentes aparecem após a primeira rodada.</p>
            )}
          </Cartao>
        </div>

      </SecaoPainel>
      <SecaoPainel id="evolucao" ativa={secao}>
      {resultados.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Cartao titulo="Caixa e lucro mensal">
            <GraficoLinhas
              rotulosX={resultados.map((r) => `M${r.rodada}`)}
              series={[
                { nome: "Caixa", cor: "#102A68", valores: resultados.map((r) => r.caixa_final) },
                { nome: "Lucro do mês", cor: "#FFC233", valores: resultados.map((r) => r.dre.lucro_liquido) },
              ]}
            />
          </Cartao>
          <Cartao titulo="Participação de mercado">
            <GraficoLinhas
              rotulosX={resultados.map((r) => `M${r.rodada}`)}
              series={[{ nome: "Participação", cor: "#FFC233", valores: resultados.map((r) => r.participacao_mercado) }]}
              formatar={(v) => percentual(v, 0)}
            />
          </Cartao>
        </div>
      )}

      </SecaoPainel>
      <SecaoPainel id="historico" ativa={secao}>
      {resultados.length > 0 ? <Historico painel={painel} /> : <Cartao titulo="Histórico"><p>Aguarde a primeira rodada concluída.</p></Cartao>}

      </SecaoPainel>
      <ViradaRodada painel={painel} podeAbrir={!eventoAberto} />
      {eventoAberto && (
        <Modal
          titulo={`Mês ${eventoAberto.rodada}: ${eventoAberto.titulo}`}
          aoFechar={fecharEvento}
          rodape={
            <Botao variante="secundario" onClick={fecharEvento}>
              Entendi
            </Botao>
          }
        >
          <p className="text-sm leading-relaxed text-slate-700">{eventoAberto.narrativa}</p>
          {ultimo && ultimo.rodada === eventoAberto.rodada && (
            <p className="mt-3 text-sm text-slate-600">
              Resultado da sua empresa no mês: <strong>{reais(ultimo.dre.lucro_liquido)}</strong>.
            </p>
          )}
        </Modal>
      )}
    </LayoutPainel>
  );
}

function simulacaoInicial(painel: PainelAluno): DecisaoSimulacao | null {
  if (!painel.turma.modo_jogo || painel.turma.modo_jogo === "LEGADO") return null;
  if (painel.decisao_atual?.simulacao) return { ...DECISAO_SIMULACAO_PADRAO, ...painel.decisao_atual.simulacao };
  const ultima = painel.ultima_decisao?.simulacao;
  if (ultima) return { ...DECISAO_SIMULACAO_PADRAO, ...ultima, comprar_mp: 0, comprar_maquinas: 0, aporte: 0, horas_extras: 0 };
  if (painel.turma.modo_jogo === "STARTUP") return { ...DECISAO_SIMULACAO_PADRAO };
  // Sugestão de quantidade inicial; a prévia do servidor calcula o efeito real.
  const estado = painel.empresa.estado_simulacao;
  const capacidadePessoas = (painel.empresa.funcionarios + 1) * (painel.turma.parametros?.produtividade_por_pessoa ?? 120);
  const capacidadeMaquinas = estado?.maquinas.filter((m) => m.ativacao <= painel.turma.rodada_atual).reduce((soma, m) => soma + m.capacidade * m.condicao, 0) ?? 0;
  const producao = Math.max(0, Math.floor(Math.min(capacidadePessoas, capacidadeMaquinas)));
  return { ...DECISAO_SIMULACAO_PADRAO, producao, comprar_mp: Math.max(0, producao - (estado?.estoque_mp.quantidade ?? 0)) };
}

function decisaoInicial(painel: PainelAluno): DecisaoEntrada {
  const base = painel.decisao_atual ?? painel.ultima_decisao;
  return {
    revisao_areas: painel.decisao_atual?.revisao_areas ?? {},
    analise_financeira: painel.decisao_atual?.analise_financeira ?? "",
    simulacao: simulacaoInicial(painel),
    plano_comercial: base?.plano_comercial ?? null,
    preco: base?.preco ?? painel.turma.parametros?.preco_referencia ?? 100,
    marketing: base?.marketing ?? 0,
    pd: base?.pd ?? 0,
    networking: base?.networking ?? 0,
    // Ações pontuais só reaparecem se forem da própria rodada
    contratar: painel.decisao_atual?.contratar ?? 0,
    demitir: painel.decisao_atual?.demitir ?? 0,
    emprestimo: painel.decisao_atual?.emprestimo ?? 0,
    amortizacao: painel.decisao_atual?.amortizacao ?? 0,
    regime_solicitado: painel.decisao_atual?.regime_solicitado ?? null,
  };
}

function assinaturaArea(d: DecisaoEntrada, area: string) {
  const op = d.simulacao;
  if (area === "decisoes") return JSON.stringify([d.preco, d.marketing, d.pd, d.networking, d.plano_comercial, op?.posicionamento, op?.canal, op?.marketing_digital, op?.salario, op?.beneficio, op?.treinamento]);
  if (area === "producao") return JSON.stringify([d.contratar, d.demitir, op?.horas_extras, op?.producao, op?.comprar_mp, op?.comprar_maquinas, op?.manutencao, op?.capacidade_nuvem, op?.centro_gravidade, op?.salario, op?.beneficio, op?.treinamento]);
  if (area === "logistica") return JSON.stringify([op?.modal, op?.centro_gravidade]);
  const { revisao_areas, ...valores } = d;
  return JSON.stringify(valores);
}
function manterRevisoes(antes: DecisaoEntrada, depois: DecisaoEntrada): DecisaoEntrada {
  const revisao = { ...depois.revisao_areas };
  for (const area of AREAS_DECISAO) {
    if (assinaturaArea(antes, area) !== assinaturaArea(depois, area)) revisao[area as keyof typeof revisao] = false;
  }
  return { ...depois, revisao_areas: revisao };
}

function FormularioDecisao({ painel, aoEnviar, area, ferramenta, aoNavegar }: { ferramenta?: string; painel: PainelAluno; area: string; aoNavegar: (area: string) => void; aoEnviar: () => Promise<PainelAluno | undefined> }) {
  const { empresa, turma } = painel;
  const p = turma.parametros!;
  const [confirmandoEnvio, setConfirmandoEnvio] = useState(false);
  const somenteLeitura = !!painel.decisao_atual?.enviada_em || (turma.modo_equipe && !painel.equipe?.pode_decidir);
  const sequencia = ["decisoes", "pd", "estrategia", "producao", "rh", "financas", ...(turma.modo_jogo === "TRADICIONAL" ? ["logistica"] : [])];
  const proxima = sequencia[sequencia.indexOf(area) + 1];
  const versaoServidor = painel.equipe?.versao_decisao ?? painel.decisao_atual?.versao ?? 0;
  const [d, setD] = useState<DecisaoEntrada>(() => decisaoInicial(painel));
  const [base, setBase] = useState(() => ({ entrada: decisaoInicial(painel), versao: versaoServidor, rodada: turma.rodada_atual }));
  const [conflitoServidor, setConflitoServidor] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [mensagem, setMensagem] = useState<{ tipo: "erro" | "sucesso"; texto: string } | null>(null);
  const [previa, setPrevia] = useState<{ chave: string; dados?: PrevisaoDecisao; erro?: string } | null>(null);
  const [tentativaPrevia, setTentativaPrevia] = useState(0);
  const chavePrevisao = JSON.stringify({ d, empresa, turma, tentativaPrevia });
  const previsao = previa?.chave === chavePrevisao ? previa.dados : undefined;
  const erroPrevisao = previa?.chave === chavePrevisao ? previa.erro : undefined;
  const alterada = JSON.stringify(d) !== JSON.stringify(base.entrada);
  const conflito = conflitoServidor || base.versao !== versaoServidor;

  // Novas versões são carregadas apenas quando o aluno não está editando.
  useEffect(() => {
    if (base.rodada !== turma.rodada_atual || !alterada) {
      const entrada = decisaoInicial(painel);
      setD(entrada);
      setBase({ entrada, versao: versaoServidor, rodada: turma.rodada_atual });
      setConflitoServidor(false);
      setMensagem(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [turma.rodada_atual, versaoServidor]);

  async function carregarDecisaoSalva() {
    setCarregando(true);
    setMensagem(null);
    try {
      const atual = await aoEnviar();
      if (!atual) throw new Error("Não foi possível carregar a decisão salva. Seus campos foram mantidos; tente novamente.");
      const entrada = decisaoInicial(atual);
      setD(entrada);
      setBase({ entrada, versao: atual.equipe?.versao_decisao ?? atual.decisao_atual?.versao ?? 0, rodada: atual.turma.rodada_atual });
      setConflitoServidor(false);
    } catch (e) {
      setMensagem({ tipo: "erro", texto: e instanceof Error ? e.message : "Erro ao carregar a decisão salva." });
    } finally {
      setCarregando(false);
    }
  }

  const atualizar = <K extends keyof DecisaoEntrada>(campo: K, valor: DecisaoEntrada[K]) =>
    setD((atual) => manterRevisoes(atual, { ...atual, [campo]: valor }));

  useEffect(() => {
    let cancelada = false;
    const { d: entrada, empresa: empresaAtual, turma: turmaAtual } = JSON.parse(chavePrevisao);
    const temporizador = window.setTimeout(async () => {
      try {
        const dados = await api.post<PrevisaoDecisao>(`/api/aluno/empresas/${empresaAtual.id}/previsao`, { ...entrada, rascunho: true, rodada: turmaAtual.rodada_atual });
        if (!cancelada) {
          if (dados.rodada !== turmaAtual.rodada_atual) {
            setPrevia({ chave: chavePrevisao, erro: "O sistema avançou a rodada. Aguarde a atualização do painel." });
          } else {
            setPrevia({ chave: chavePrevisao, dados });
          }
        }
      } catch (e) {
        if (!cancelada) setPrevia({ chave: chavePrevisao, erro: e instanceof Error ? e.message : "Erro ao calcular a prévia." });
      }
    }, 250);
    return () => {
      cancelada = true;
      window.clearTimeout(temporizador);
    };
  }, [chavePrevisao]);

  async function salvar(rascunho: boolean, avancar = false) {
    if (somenteLeitura || carregando || conflito) return;
    setCarregando(true);
    setMensagem(null);
    try {
      const salva = await api.put<Decisao>(`/api/aluno/empresas/${empresa.id}/decisao`, { ...d, rascunho, versao: base.versao, rodada: base.rodada });
      const entrada = { ...d, preco: salva.preco, marketing: salva.marketing, plano_comercial: salva.plano_comercial, simulacao: salva.simulacao };
      setD(entrada);
      setBase({ entrada, versao: salva.versao, rodada: turma.rodada_atual });
      setConflitoServidor(false);
      setMensagem({ tipo: "sucesso", texto: rascunho ? `Rascunho da versão ${salva.versao} salvo. Ele ainda não foi enviado para a rodada.` : "Decisão final enviada pela equipe. Acompanhe o fechamento da rodada." });
      await aoEnviar();
      if(avancar && proxima) aoNavegar(proxima);
    } catch (e) {
      if (e instanceof ErroApi && e.status === 409) {
        setConflitoServidor(true);
        await aoEnviar();
      }
      setMensagem({ tipo: "erro", texto: e instanceof Error ? e.message : "Erro ao enviar." });
    } finally {
      setCarregando(false);
    }
  }

  return (
    <Cartao
      titulo={`${area === "estrategia" ? "Ferramentas estratégicas e segmentação" : area === "pd" ? "P&D - tecnologia e inovação" : area === "rh" ? "Recursos humanos" : area === "financas" ? "Planejamento financeiro" : area === "producao" ? "Produção e operação" : area === "logistica" ? "Logística" : "Decisões comerciais"} · mês ${turma.rodada_atual}`}
      acao={
        painel.decisao_atual ? (
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${painel.decisao_atual?.enviada_em ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{painel.decisao_atual.enviada_em ? "Decisão final enviada" : `Rascunho · versão ${versaoServidor}`}</span>
        ) : (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">Pendente</span>
        )
      }
    >
      <form onSubmit={e => {e.preventDefault();setConfirmandoEnvio(true);}} className="space-y-6">
        {painel.decisao_atual?.enviada_em && <div role="status" className="sticky top-0 z-20 rounded-xl border border-emerald-300 bg-emerald-50 p-4 font-semibold text-emerald-900">🔒 Decisões salvas! Modo de leitura ativado. Aguardando o encerramento do prazo pelo professor.</div>}
        {somenteLeitura && !painel.decisao_atual?.enviada_em && <Aviso tipo="info">Você está em modo de visualização. Discuta as decisões com o líder, que registra e envia pela equipe.</Aviso>}
        <p className="rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-900">As escolhas de Marketing, Finanças, Produção e Logística compõem uma única decisão. Ao enviar, todas as áreas preenchidas são registradas juntas.</p>
        <div className="rounded-xl border border-blue-200 p-4"><h3 className="font-bold">Revisão antes do envio</h3><p className="mt-1 text-sm text-slate-600">Confira cada área e marque a revisão. Alterar escolhas pede nova revisão das áreas afetadas. Valores zero são escolhas válidas para ações opcionais. Todas as áreas aplicáveis precisam estar revisadas para o envio final.</p><div className="mt-3 grid gap-2 sm:grid-cols-2">{AREAS_DECISAO.map(id => {
          const aplicavel = id !== "logistica" || turma.modo_jogo === "TRADICIONAL";
          const revisada = !!d.revisao_areas?.[id as keyof NonNullable<DecisaoEntrada["revisao_areas"]>];
          return <button type="button" key={id} onClick={() => aoNavegar(id)} className={`rounded-lg border p-3 text-left text-sm ${aplicavel && revisada ? "border-emerald-300 bg-emerald-50" : "border-amber-200 bg-amber-50"}`}>{id === "decisoes" ? "Produtos e marketing" : id === "financas" ? "Finanças" : id === "producao" ? "Produção" : "Logística"} · {aplicavel ? revisada ? "Revisado ✓" : "Revisar →" : "Sem decisão neste modelo"}</button>;
        })}</div><label className="mt-4 flex items-center gap-3 text-sm font-semibold"><input type="checkbox" disabled={somenteLeitura || (area === "logistica" && turma.modo_jogo !== "TRADICIONAL")} checked={!!d.revisao_areas?.[(area === "estrategia" ? "decisoes" : (AREA_REVISAO[area] || area)) as keyof NonNullable<DecisaoEntrada["revisao_areas"]>]} onChange={e => setD(atual => ({ ...atual, revisao_areas: { ...atual.revisao_areas, [area === "estrategia" ? "decisoes" : (AREA_REVISAO[area] || area)]: e.target.checked } }))} />Conferi os valores desta área</label><p className="mt-2 text-xs text-slate-500">As revisões ficam registradas ao salvar ou enviar esta versão da decisão.</p></div>
        {turma.modo_equipe && <p className="text-sm text-slate-600">Somente o líder altera e envia. Todos podem consultar o planejamento e contribuir na discussão. O envio final será bloqueado se houver etapas obrigatórias pendentes.</p>}
        {conflito && <div className="space-y-2"><Aviso tipo="info">Outra atualização chegou enquanto você editava. Seus campos foram mantidos. Carregue a decisão salva da empresa antes de continuar; essa ação substitui os valores do formulário.</Aviso><Botao type="button" variante="secundario" disabled={carregando} onClick={carregarDecisaoSalva}>Carregar decisão salva</Botao></div>}
        <RevisaoCampos.Provider value={!!d.revisao_areas?.[(area === "estrategia" ? "decisoes" : (AREA_REVISAO[area] || area)) as keyof NonNullable<DecisaoEntrada["revisao_areas"]>]}><fieldset disabled={carregando || somenteLeitura} className={`space-y-6 ${somenteLeitura ? "opacity-50 pointer-events-none" : ""}`}>
        <div hidden={area !== "decisoes" && area !== "estrategia" && area !== "pd"}>
        <div hidden={area === "pd"}><EditorMix ferramenta={ferramenta || "SWOT"} precoAtual={d.preco} visao={area === "estrategia" ? "estrategia" : "mix"} aoNavegar={aoNavegar} empresaId={empresa.id} rodada={turma.rodada_atual} plano={d.plano_comercial} aoMudar={(plano,total,preco)=>!somenteLeitura && setD(atual=>manterRevisoes(atual,{...atual,plano_comercial:plano,marketing:total,preco:preco??atual.preco,simulacao:atual.simulacao?{...atual.simulacao,marketing_digital:0}:null}))} /></div>
          <div hidden={area !== "decisoes"}><Secao titulo="Mercado e posicionamento">
          <div hidden={!!d.plano_comercial?.produtos?.length}><Campo
            rotulo="Preço de venda (por unidade)"
            ajuda={`Preço de referência do mercado: ${reais(p.preco_referencia)}. Custo da mercadoria: ${reais(d.plano_comercial?.custo_unitario ?? p.custo_unitario)}.`}
          >
            <ControleVisual rotulo="Preço de venda" valor={d.preco} aoMudar={(v) => atualizar("preco", v)} minimo={0.01} limite={p.preco_referencia * 3} />
          </Campo>
          </div><Campo rotulo="Marketing (no mês)" ajuda={d.plano_comercial ? "Inclui mídia, produção e serviços; somente produzir uma peça não compra audiência." : `Fortalece a marca. Índice atual: ${umDecimal(empresa.marca)}.`}>
            {d.plano_comercial ? <p className="font-semibold">{reais(d.marketing)} · mídia + produção e serviços</p> : <ControleVisual rotulo="Investimento em marketing" valor={d.marketing} aoMudar={(v) => atualizar("marketing", v)} limite={Math.max(1000, empresa.caixa)} />}
          </Campo>
          </Secao></div><div hidden={area !== "pd"}><Secao titulo="Pesquisa e desenvolvimento"><Campo rotulo="Pesquisa e desenvolvimento (no mês)" ajuda={`Melhora a qualidade percebida. Índice atual: ${umDecimal(empresa.qualidade)}.`}>
            <ControleVisual rotulo="Tecnologia e melhoria do produto (P&D)" valor={d.pd} aoMudar={(v) => atualizar("pd", v)} limite={Math.max(1000, empresa.caixa)} />
          </Campo>
          <Campo rotulo="Networking e capacitação (no mês)" ajuda="Rede de contadores e parceiros. Networking ≥ 30 evita multas em fiscalizações.">
            <ControleVisual rotulo="Networking e capacitação" valor={d.networking} aoMudar={(v) => atualizar("networking", v)} limite={Math.max(1000, empresa.caixa)} />
          </Campo>
        </Secao></div>

        </div>
        <div hidden={area !== "rh"}>
        <Secao titulo="Funcionários e capacidade de atendimento">
          <Campo rotulo="Contratar" ajuda={`Salário-base ${reais(p.salario_base)}. A prévia aplica os encargos do regime efetivo.`}>
            <ControleVisual rotulo="Contratar funcionários" moeda={false} inteiro valor={d.contratar} aoMudar={(v) => atualizar("contratar", v)} limite={20} />
          </Campo>
          <Campo rotulo="Demitir" ajuda={`Hoje: ${empresa.funcionarios} funcionário(s). Rescisão custa um salário.`}>
            <ControleVisual rotulo="Demitir funcionários" moeda={false} inteiro valor={d.demitir} aoMudar={(v) => atualizar("demitir", v)} limite={empresa.funcionarios} />
          </Campo>
        </Secao>

        </div>
        <div hidden={area !== "financas"}>
        <Campo pendente={!d.analise_financeira.trim()} rotulo="Análise financeira da equipe" ajuda="Explique margem, custos, fluxo de caixa, capital de giro e riscos das escolhas. Esta análise é responsabilidade da equipe."><textarea aria-label="Análise financeira da equipe" className={`${estiloEntrada} min-h-32`} maxLength={6000} value={d.analise_financeira} onChange={e=>atualizar("analise_financeira",e.target.value)} /></Campo>
        <div className="mb-4 rounded-xl border-l-4 border-blue-600 bg-blue-50 p-4 text-sm"><h3 className="font-bold text-blue-900">Planeje antes de enviar</h3><p className="mt-2">Use preço de venda, custo unitário e despesas para analisar a margem e o ponto de equilíbrio. A prévia abaixo reúne os valores calculados para você conferir seu planejamento.</p><p className="mt-2 font-semibold">Preço escolhido: {reais(d.preco)} · Custo unitário: {reais(d.plano_comercial?.custo_unitario ?? p.custo_unitario)} · Caixa atual: {reais(empresa.caixa)}</p></div>
        {d.emprestimo > 0 && <Aviso tipo="info">Atenção: dinheiro do banco tem custo alto e pode comprometer a empresa. Juros estimados deste pedido: até {reais(Math.min(d.emprestimo, Math.max(0, p.limite_credito - empresa.divida)) * p.taxa_juros_mensal)} por mês, além da dívida atual, à taxa de {percentual(p.taxa_juros_mensal, 2)}. Os juros reduzem lucro e capital de giro, podem subir com a Selic e continuam enquanto houver saldo devedor. O principal precisa ser devolvido; crédito depende do caixa e do limite disponível.</Aviso>}
        <Secao titulo="Finanças e tributos">
          <Campo
            rotulo="Novo empréstimo"
            ajuda={`Juros de ${percentual(p.taxa_juros_mensal, 2)} ao mês. Limite disponível: ${reais(Math.max(0, p.limite_credito - empresa.divida))}.`}
          >
            <ControleVisual rotulo="Novo empréstimo" valor={d.emprestimo} aoMudar={(v) => atualizar("emprestimo", v)} limite={Math.max(0, p.limite_credito - empresa.divida)} />
          </Campo>
          <Campo rotulo="Amortizar dívida" ajuda={`Dívida atual: ${reais(empresa.divida)}.`}>
            <ControleVisual rotulo="Amortizar dívida" valor={d.amortizacao} aoMudar={(v) => atualizar("amortizacao", v)} limite={empresa.divida} />
          </Campo>
          <Campo
            rotulo="Regime tributário"
            ajuda={
              empresa.regime_pretendido
                ? `Migração obrigatória: a empresa passa ao ${NOME_REGIME[empresa.regime_pretendido]} neste mês.`
                : empresa.regime_tributario === "MEI"
                ? `Faturamento no ano: ${reais(empresa.faturamento_ano)} de ${reais(p.teto_mei_anual)} do teto do MEI.`
                : "A mudança vale a partir deste mês."
            }
          >
            <select
              className={estiloEntrada}
              value={d.regime_solicitado ?? ""}
              onChange={(e) => atualizar("regime_solicitado", (e.target.value || null) as RegimeTributario | null)}
            >
              <option value="">Manter {NOME_REGIME[empresa.regime_tributario]}</option>
              {(Object.keys(NOME_REGIME) as RegimeTributario[])
                .filter((r) => r !== empresa.regime_tributario)
                .map((r) => (
                  <option key={r} value={r}>
                    Mudar para {NOME_REGIME[r]}
                  </option>
                ))}
            </select>
          </Campo>
        </Secao>

        </div>
        {turma.modo_jogo === "LEGADO" && ["producao", "logistica"].includes(area) && <div className="rounded-xl border-l-4 border-blue-600 bg-blue-50 p-5"><h3 className="font-bold">{area === "producao" ? "Capacidade no modelo básico" : "Logística no modelo básico"}</h3><p className="mt-2 text-sm">{area === "producao" ? "Neste modelo, a capacidade depende da equipe de funcionários. Estoques, máquinas e planejamento de produção são controles do modelo Empresa tradicional." : "Este modelo não possui escolha de frete ou entregas. Esses controles estão disponíveis no modelo Empresa tradicional; no modelo Startup, a operação é digital."}</p><p className="mt-2 text-sm">Confira a capacidade e os gastos previstos na prévia abaixo.</p></div>}
        {turma.modo_jogo !== "LEGADO" && d.simulacao && <ControlesSimulacao rodada={turma.rodada_atual} area={area} modo={turma.modo_jogo} valores={d.simulacao} aoMudar={(simulacao) => atualizar("simulacao", simulacao)} config={turma.parametros?.configuracao_simulacao ?? turma.configuracao_simulacao ?? CONFIGURACAO_MOTOR_PADRAO} salarioBase={p.salario_base} marketing={d.marketing} mixSelecionado={!!d.plano_comercial} />}

        <div className="rounded-lg bg-slate-50 p-4 text-sm">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">Prévia do mês</p>
          {!previsao && !erroPrevisao && <p role="status">Calculando prévia…</p>}
          {erroPrevisao && (
            <div className="space-y-2">
              <Aviso>{erroPrevisao}</Aviso>
              <Botao type="button" variante="secundario" onClick={() => setTentativaPrevia((atual) => atual + 1)}>
                Tentar calcular novamente
              </Botao>
            </div>
          )}
          {previsao && (
            <>
              <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 sm:grid-cols-3">
                <Previa rotulo="Capacidade de produção" valor={`${inteiro(previsao.capacidade)} un.`} />
                <Previa rotulo="Folha com encargos" valor={reais(previsao.folha)} />
                <Previa rotulo="Gastos previstos do mês" valor={reais(previsao.gastos_previstos)} />
                <Previa rotulo="Margem por unidade" valor={reais(previsao.margem_unitaria)} />
                <Previa
                  rotulo="Ponto de equilíbrio"
                  valor={previsao.ponto_equilibrio !== null ? `${inteiro(Math.ceil(previsao.ponto_equilibrio))} un.` : "sem margem"}
                />
                <Previa rotulo="Caixa após financiamento" valor={reais(previsao.caixa_disponivel)} />
                <Previa rotulo="Empréstimo aprovado na prévia" valor={reais(previsao.emprestimo_aprovado)} />
                <Previa rotulo="Amortização aplicada" valor={reais(previsao.amortizacao_aplicada)} />
                <Previa rotulo="Regime considerado" valor={NOME_REGIME[previsao.regime]} />
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Antes de tributos, vendas e novos eventos. Inclui juros, royalties de franquia e efeitos ainda ativos de rodadas anteriores.
                O caixa acima é anterior aos gastos do mês; o resultado final depende do mercado e do evento no fechamento.
              </p>
              {previsao.ponto_equilibrio !== null && previsao.ponto_equilibrio > previsao.capacidade && (
                <p className="mt-2 text-xs font-semibold text-red-700">
                  Atenção: mesmo vendendo toda a capacidade, a empresa não cobre os gastos previstos deste mês.
                </p>
              )}
              {previsao.alertas.map((alerta) => <p key={alerta} className="mt-2 text-xs font-semibold text-amber-800">{alerta}</p>)}
              {previsao.simulacao && <PreviaOperacional simulacao={previsao.simulacao} modo={turma.modo_jogo} />}
            </>
          )}
        </div>
        </fieldset></RevisaoCampos.Provider>

        {mensagem && <Aviso tipo={mensagem.tipo}>{mensagem.texto}</Aviso>}
        {!somenteLeitura && <><p className="text-xs text-slate-600">O rascunho pode ficar incompleto. No envio final, o programa informa as pendências e impede o envio até que sejam resolvidas.</p>
        {!!painel.pendencias_envio?.length && <Aviso tipo="info"><p className="font-bold">Pendências da versão salva:</p><ul className="list-disc pl-5">{painel.pendencias_envio.map(p=><li key={p}>{p}</li>)}</ul></Aviso>}
        <div className="flex flex-wrap justify-end gap-2"><Botao type="button" variante="secundario" disabled={carregando||conflito} onClick={()=>salvar(true)}>Salvar rascunho</Botao>{proxima&&<Botao type="button" variante="secundario" disabled={carregando||conflito} onClick={()=>salvar(true,true)}>Salvar e ir para a próxima etapa →</Botao>}<Botao type="submit" carregando={carregando} disabled={conflito}>Enviar decisão final</Botao></div></>}
      </form>
      {confirmandoEnvio && <Modal titulo="Confirmar decisão final" aoFechar={()=>setConfirmandoEnvio(false)}><p className="text-sm">Esta é a decisão final da equipe para este mês? Após enviar, todas as escolhas ficam visíveis em modo de leitura até a próxima rodada. Use o rascunho se ainda precisar alterar algo.</p><div className="mt-6 flex justify-end gap-3"><Botao variante="secundario" onClick={()=>setConfirmandoEnvio(false)}>Voltar e revisar</Botao><Botao carregando={carregando} onClick={()=>{setConfirmandoEnvio(false);salvar(false);}}>Confirmar envio final</Botao></div></Modal>}
    </Cartao>
  );
}

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <fieldset>
      <legend className="mb-3 border-b border-slate-200 pb-1 text-sm font-semibold text-marinho">{titulo}</legend>
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  );
}

function Previa({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{rotulo}</p>
      <p className="font-semibold text-marinho">{valor}</p>
    </div>
  );
}

function Historico({ painel }: { painel: PainelAluno }) {
  const eventos = new Map(painel.eventos.map((e) => [e.rodada, e.titulo]));
  const [rodadaSelecionada, setRodadaSelecionada] = useState(painel.resultados[painel.resultados.length - 1]?.rodada);
  const temDetalhes = painel.resultados.some((r) => r.detalhes_simulacao);
  const selecionado = painel.resultados.find((r) => r.rodada === rodadaSelecionada);
  return (
    <Cartao titulo="Histórico">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-slate-500">
              <th className="pb-2">Mês</th>
              <th className="pb-2 text-right">Preço</th>
              <th className="pb-2 text-right">Vendas</th>
              <th className="pb-2 text-right">Receita</th>
              <th className="pb-2 text-right">Lucro</th>
              <th className="pb-2 text-right">Caixa</th>
              <th className="pb-2">Regime</th>
              <th className="pb-2">Evento</th>
              {temDetalhes && <th className="pb-2">Demonstrativos</th>}
            </tr>
          </thead>
          <tbody>
            {[...painel.resultados].reverse().map((r) => (
              <tr key={r.rodada} className="border-t border-slate-100">
                <td className="py-1.5">{r.rodada}</td>
                <td className="py-1.5 text-right">{reais(r.preco)}</td>
                <td className="py-1.5 text-right">{inteiro(r.unidades_vendidas)}</td>
                <td className="py-1.5 text-right">{reais(r.dre.receita)}</td>
                <td className={`py-1.5 text-right ${r.dre.lucro_liquido < 0 ? "text-red-700" : "text-emerald-700"}`}>
                  {reais(r.dre.lucro_liquido)}
                </td>
                <td className="py-1.5 text-right">{reais(r.caixa_final)}</td>
                <td className="py-1.5">{NOME_REGIME[r.regime]}</td>
                <td className="py-1.5 text-slate-500">{eventos.get(r.rodada) ?? "—"}</td>
                {temDetalhes && <td className="py-1.5">{r.detalhes_simulacao && <button className={`rounded-md px-2 py-1 text-xs font-semibold ${rodadaSelecionada === r.rodada ? "bg-marinho text-white" : "bg-slate-100 text-marinho"}`} aria-pressed={rodadaSelecionada === r.rodada} onClick={() => setRodadaSelecionada(r.rodada)}>Ver mês {r.rodada}</button>}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {selecionado?.detalhes_simulacao && <div className="mt-5 space-y-4"><h3 className="text-sm font-semibold text-marinho">Demonstrativos e operação do mês {selecionado.rodada}</h3><RelatorioFinanceiro detalhes={selecionado.detalhes_simulacao} /></div>}
    </Cartao>
  );
}

function IndicadoresFinanceiros({ resultado }: { resultado: PainelAluno["resultados"][number] }) {
  const { dre, detalhes_simulacao: detalhes } = resultado;
  const margem = dre.receita > 0 ? dre.lucro_liquido / dre.receita : null;
  const b = detalhes?.balanco;
  const ativos = b ? (b.ativo_total ?? Math.max(0,b.caixa) + b.receber + b.estoques + b.imobilizado) : null;
  const passivos = b ? (b.passivo_total ?? b.pagar + b.divida + Math.max(0,-b.caixa)) : null;
  return <Cartao titulo={`KPIs e indicadores financeiros · rodada ${resultado.rodada}`}>
    <dl className="grid gap-4 sm:grid-cols-3">
      <div><dt className="text-sm text-slate-500">Margem líquida</dt><dd className="font-bold text-marinho">{margem === null ? "—" : percentual(margem)}</dd><p className="text-xs text-slate-500">Lucro líquido dividido pela receita.</p></div>
      <div><dt className="text-sm text-slate-500">Participação no mercado</dt><dd className="font-bold text-marinho">{percentual(resultado.participacao_mercado)}</dd><p className="text-xs text-slate-500">Parcela do mercado conquistada nesta rodada.</p></div>
      <div><dt className="text-sm text-slate-500">Atendimento da demanda</dt><dd className="font-bold text-marinho">{resultado.demanda > 0 ? percentual(resultado.unidades_vendidas / resultado.demanda) : "—"}</dd><p className="text-xs text-slate-500">Unidades vendidas divididas pela demanda da empresa.</p></div>
      {b && <>
        <div><dt className="text-sm text-slate-500">Endividamento sobre ativos</dt><dd className="font-bold text-marinho">{ativos !== null && ativos > 0 && passivos !== null ? percentual(passivos / ativos) : "—"}</dd><p className="text-xs text-slate-500">Contas a pagar e dívida divididas pelo total de ativos.</p></div>
        <div><dt className="text-sm text-slate-500">Retorno sobre o patrimônio · rodada</dt><dd className="font-bold text-marinho">{b.patrimonio > 0 ? percentual(dre.lucro_liquido / b.patrimonio) : "—"}</dd><p className="text-xs text-slate-500">Lucro da rodada dividido pelo patrimônio final; não é uma taxa anual.</p></div>
        <div><dt className="text-sm text-slate-500">Caixa operacional</dt><dd className="font-bold text-marinho">{reais(detalhes!.dfc.operacional)}</dd><p className="text-xs text-slate-500">Recebimentos menos pagamentos operacionais.</p></div>
      </>}
    </dl>
    <p className="mt-3 text-xs text-slate-500">“—” indica ausência de uma base válida para cálculo. Compare com as rodadas anteriores e com os demonstrativos.</p>
    <details className="mt-5 rounded-xl border border-slate-200 p-4"><summary className="cursor-pointer font-semibold">Ver balanço e demonstrativos completos</summary>
    {resultado.balanco_basico && <div className="mt-5 rounded border p-4"><h3 className="font-semibold">Balanço patrimonial · modelo básico · rodada {resultado.rodada}</h3><p className="my-2 text-xs text-slate-500">O modelo básico opera à vista, sem estoques, imobilizado ou contas a prazo. Saldo de caixa negativo aparece como cheque especial no passivo.</p><dl className="grid gap-3 sm:grid-cols-3">{([
      ["Caixa e bancos",resultado.balanco_basico.caixa],
      ["Empréstimos",resultado.balanco_basico.emprestimos],
      ["Cheque especial",resultado.balanco_basico.cheque_especial],
      ["Ativo total",resultado.balanco_basico.ativo_total],
      ["Passivo total",resultado.balanco_basico.passivo_total],
      ["Patrimônio líquido",resultado.balanco_basico.patrimonio_liquido]
    ] as const).map(([nome,valor])=><div key={nome}><dt className="text-sm text-slate-500">{nome}</dt><dd className="font-bold">{reais(valor)}</dd></div>)}</dl></div>}
    {!detalhes && <ResultadoProdutos produtos={resultado.produtos_resultado??[]}/>}
    {detalhes && <div className="mt-5"><RelatorioFinanceiro detalhes={detalhes} /></div>}
    </details>
  </Cartao>;
}
