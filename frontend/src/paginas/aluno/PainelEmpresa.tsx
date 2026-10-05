import React, { useCallback, useEffect, useState } from "react";

import { api } from "../../api";
import {
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
import type { DecisaoEntrada, EventoRodada, PainelAluno, PrevisaoDecisao, RegimeTributario } from "../../tipos";

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

  const carregar = useCallback(async () => {
    try {
      const dados = await api.get<PainelAluno>(`/api/aluno/empresas/${empresaId}`);
      setPainel(dados);
      const ultimoEvento = dados.eventos[dados.eventos.length - 1];
      if (ultimoEvento && ultimoEvento.rodada > lerEventoVisto(empresaId)) {
        setEventoAberto(ultimoEvento);
      }
      setErro(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar.");
    }
  }, [empresaId]);

  useEffect(() => {
    carregar();
    const intervalo = window.setInterval(carregar, INTERVALO_ATUALIZACAO_MS);
    return () => window.clearInterval(intervalo);
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
    <div className="space-y-6">
      <div className="rounded-xl bg-marinho p-5 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-ouro">{turma.nome}</p>
            <h1 className="text-2xl font-bold">{empresa.nome}</h1>
            <p className="mt-1 text-xs text-white/60">
              {NOME_GEM[empresa.tipo_entrada_gem]} · {NOME_DORNELAS[empresa.classe_dornelas]}
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <SeloFase fase={empresa.fase_atual} />
            <p className="text-sm text-white/80">
              {encerrada ? "Simulação encerrada" : `Mês ${turma.rodada_atual} de ${turma.total_rodadas}`}
            </p>
          </div>
        </div>

        {empresa.fase_atual === "SOBREVIVENCIA" && (
          <div className="mt-4 animate-pulse rounded-lg bg-red-600 px-4 py-2 text-sm font-bold uppercase tracking-wide">
            Alerta: estado de sobrevivência — o caixa não cobre um mês de custos fixos
          </div>
        )}

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
      </div>

      {erro && <Aviso>{erro}</Aviso>}

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
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
            <FormularioDecisao key={empresa.id} painel={painel} aoEnviar={carregar} />
          )}
        </div>
        <div className="space-y-6 lg:col-span-2">
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
                <TabelaDre dre={ultimo.dre} />
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
                Nenhuma rodada fechada ainda. Envie suas decisões e aguarde o professor fechar o mês.
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
      </div>

      {resultados.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Cartao titulo="Caixa e lucro mensal">
            <GraficoLinhas
              rotulosX={resultados.map((r) => `M${r.rodada}`)}
              series={[
                { nome: "Caixa", cor: "#0B2545", valores: resultados.map((r) => r.caixa_final) },
                { nome: "Lucro do mês", cor: "#C5A059", valores: resultados.map((r) => r.dre.lucro_liquido) },
              ]}
            />
          </Cartao>
          <Cartao titulo="Participação de mercado">
            <GraficoLinhas
              rotulosX={resultados.map((r) => `M${r.rodada}`)}
              series={[{ nome: "Participação", cor: "#C5A059", valores: resultados.map((r) => r.participacao_mercado) }]}
              formatar={(v) => percentual(v, 0)}
            />
          </Cartao>
        </div>
      )}

      {resultados.length > 0 && <Historico painel={painel} />}

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
    </div>
  );
}

function decisaoInicial(painel: PainelAluno): DecisaoEntrada {
  const base = painel.decisao_atual ?? painel.ultima_decisao;
  return {
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

function FormularioDecisao({ painel, aoEnviar }: { painel: PainelAluno; aoEnviar: () => Promise<void> }) {
  const { empresa, turma } = painel;
  const p = turma.parametros!;
  const [d, setD] = useState<DecisaoEntrada>(() => decisaoInicial(painel));
  const [carregando, setCarregando] = useState(false);
  const [mensagem, setMensagem] = useState<{ tipo: "erro" | "sucesso"; texto: string } | null>(null);
  const [previa, setPrevia] = useState<{ chave: string; dados?: PrevisaoDecisao; erro?: string } | null>(null);
  const [tentativaPrevia, setTentativaPrevia] = useState(0);
  const chavePrevisao = JSON.stringify({ d, empresa, turma, tentativaPrevia });
  const previsao = previa?.chave === chavePrevisao ? previa.dados : undefined;
  const erroPrevisao = previa?.chave === chavePrevisao ? previa.erro : undefined;

  // Ao mudar de rodada, recomeça a partir da última decisão
  useEffect(() => {
    setD(decisaoInicial(painel));
    setMensagem(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [turma.rodada_atual]);

  const atualizar = <K extends keyof DecisaoEntrada>(campo: K, valor: DecisaoEntrada[K]) =>
    setD((atual) => ({ ...atual, [campo]: valor }));

  useEffect(() => {
    let cancelada = false;
    const { d: entrada, empresa: empresaAtual, turma: turmaAtual } = JSON.parse(chavePrevisao);
    const temporizador = window.setTimeout(async () => {
      try {
        const dados = await api.post<PrevisaoDecisao>(`/api/aluno/empresas/${empresaAtual.id}/previsao`, entrada);
        if (!cancelada) {
          if (dados.rodada !== turmaAtual.rodada_atual) {
            setPrevia({ chave: chavePrevisao, erro: "O professor avançou a rodada. Aguarde a atualização do painel." });
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

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!previsao || carregando) return;
    setCarregando(true);
    setMensagem(null);
    try {
      await api.put(`/api/aluno/empresas/${empresa.id}/decisao`, d);
      setMensagem({ tipo: "sucesso", texto: "Decisões enviadas. Você pode alterá-las até o professor fechar o mês." });
      await aoEnviar();
    } catch (e) {
      setMensagem({ tipo: "erro", texto: e instanceof Error ? e.message : "Erro ao enviar." });
    } finally {
      setCarregando(false);
    }
  }

  return (
    <Cartao
      titulo={`Decisões para o mês ${turma.rodada_atual}`}
      acao={
        painel.decisao_atual ? (
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">Enviada</span>
        ) : (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">Pendente</span>
        )
      }
    >
      <form onSubmit={enviar} className="space-y-6">
        <Secao titulo="Mercado e posicionamento">
          <Campo
            rotulo="Preço de venda (por unidade)"
            ajuda={`Preço de referência do mercado: ${reais(p.preco_referencia)}. Custo da mercadoria: ${reais(p.custo_unitario)}.`}
          >
            <EntradaNumero moeda valor={d.preco} aoMudar={(v) => atualizar("preco", v)} minimo={0.01} />
          </Campo>
          <Campo rotulo="Marketing (no mês)" ajuda={`Fortalece a marca. Índice atual: ${umDecimal(empresa.marca)}.`}>
            <EntradaNumero moeda valor={d.marketing} aoMudar={(v) => atualizar("marketing", v)} />
          </Campo>
          <Campo rotulo="Pesquisa e desenvolvimento (no mês)" ajuda={`Melhora a qualidade percebida. Índice atual: ${umDecimal(empresa.qualidade)}.`}>
            <EntradaNumero moeda valor={d.pd} aoMudar={(v) => atualizar("pd", v)} />
          </Campo>
          <Campo rotulo="Networking e capacitação (no mês)" ajuda="Rede de contadores e parceiros. Networking ≥ 30 evita multas em fiscalizações.">
            <EntradaNumero moeda valor={d.networking} aoMudar={(v) => atualizar("networking", v)} />
          </Campo>
        </Secao>

        <Secao titulo="Equipe">
          <Campo rotulo="Contratar" ajuda={`Salário-base ${reais(p.salario_base)}. A prévia aplica os encargos do regime efetivo.`}>
            <EntradaNumero inteiro valor={d.contratar} aoMudar={(v) => atualizar("contratar", v)} />
          </Campo>
          <Campo rotulo="Demitir" ajuda={`Hoje: ${empresa.funcionarios} funcionário(s). Rescisão custa um salário.`}>
            <EntradaNumero inteiro valor={d.demitir} aoMudar={(v) => atualizar("demitir", v)} />
          </Campo>
        </Secao>

        <Secao titulo="Finanças e tributos">
          <Campo
            rotulo="Novo empréstimo"
            ajuda={`Juros de ${percentual(p.taxa_juros_mensal, 2)} ao mês. Limite disponível: ${reais(Math.max(0, p.limite_credito - empresa.divida))}.`}
          >
            <EntradaNumero moeda valor={d.emprestimo} aoMudar={(v) => atualizar("emprestimo", v)} />
          </Campo>
          <Campo rotulo="Amortizar dívida" ajuda={`Dívida atual: ${reais(empresa.divida)}.`}>
            <EntradaNumero moeda valor={d.amortizacao} aoMudar={(v) => atualizar("amortizacao", v)} />
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
            </>
          )}
        </div>

        {mensagem && <Aviso tipo={mensagem.tipo}>{mensagem.texto}</Aviso>}
        <div className="flex justify-end">
          <Botao type="submit" carregando={carregando} disabled={!previsao}>
            {painel.decisao_atual ? "Atualizar decisões" : "Enviar decisões"}
          </Botao>
        </div>
      </form>
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Cartao>
  );
}
