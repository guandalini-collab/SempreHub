import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { percentual, reais } from "../formatos";
import type { Decisao, Empresa, Resultado, Turma } from "../tipos";
import type { ModoJogo } from "../tiposSimulacao";

type BoletimItem = { titulo: string; resumo: string; competencia?: string | null; referencia: string; setores_afetados?: string[] };
type Boletim = { itens: BoletimItem[]; consultado_em: string | null; setor_sem_item_especifico?: boolean };
type Semaforo = "verde" | "amarelo" | "vermelho" | "neutro";
type Metrica = { nome: string; ajuda: string; valor: number | null; anterior: number | null; formato: "moeda" | "percentual" | "numero" | "pontos" | "escala" | "semanas" };

const cor: Record<Semaforo, string> = {
  verde: "border-emerald-200 bg-emerald-50",
  amarelo: "border-amber-200 bg-amber-50",
  vermelho: "border-red-200 bg-red-50",
  neutro: "border-slate-200 bg-white",
};
const nomeCor: Record<Semaforo, string> = { verde: "Saudável", amarelo: "Atenção", vermelho: "Crítico", neutro: "Dados parciais" };
const ponto: Record<Semaforo, string> = { verde: "bg-emerald-600", amarelo: "bg-amber-500", vermelho: "bg-red-600", neutro: "bg-slate-400" };

function numero(resultado: Resultado | undefined, chave: string): number | null {
  const valor = resultado?.detalhes_simulacao?.operacao?.[chave];
  return typeof valor === "number" && Number.isFinite(valor) ? valor : null;
}
function dividir(a: number | null | undefined, b: number | null | undefined, fator = 1): number | null {
  return a != null && b != null && b > 0 ? (a / b) * fator : null;
}
function unidade(valor: number | null, formato: Metrica["formato"]) {
  if (valor == null || !Number.isFinite(valor)) return "N/D";
  if (formato === "moeda") return reais(valor);
  if (formato === "percentual") return percentual(valor, 1);
  if (formato === "pontos") return `${valor.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} pontos`;
  if (formato === "escala") return `${valor.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
  if (formato === "semanas") return `${valor.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} sem.`;
  return valor.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}
function delta(atual: number | null, anterior: number | null, formato: Metrica["formato"]) {
  if (atual == null || anterior == null || !Number.isFinite(atual) || !Number.isFinite(anterior)) return "sem histórico";
  const diferenca = atual - anterior;
  if (Math.abs(diferenca) < 0.00001) return "— sem mudança";
  const prefixo = diferenca > 0 ? "▲" : "▼";
  const absoluto = unidade(Math.abs(diferenca), formato);
  return `${prefixo} ${absoluto}`;
}
function metrica(nome: string, ajuda: string, valor: number | null, anterior: number | null, formato: Metrica["formato"]): Metrica {
  return { nome, ajuda, valor, anterior, formato };
}
function grauFinancas(resultado: Resultado, empresa: Empresa): Semaforo {
  const custoSemanal = Math.max(1, (resultado.dre.custos_fixos ?? 0) + (resultado.dre.folha ?? 0));
  const semanas = Math.max(0, empresa.caixa) / custoSemanal;
  return semanas > 8 ? "verde" : semanas >= 4 ? "amarelo" : "vermelho";
}
function grauRh(resultado: Resultado): Semaforo {
  const moral = numero(resultado, "moral");
  const extras = numero(resultado, "horas_extras") ?? 0;
  const estresseEstimado = Math.min(100, extras / 40 * 100);
  if (moral == null) return "neutro";
  if (moral < 50 || estresseEstimado > 80) return "vermelho";
  if (moral <= 75 || estresseEstimado >= 50) return "amarelo";
  return "verde";
}
function grauOperacao(resultado: Resultado, modo: ModoJogo): Semaforo {
  if (modo === "STARTUP") {
    const naoAtendidos = numero(resultado, "clientes_nao_atendidos") ?? 0;
    const capacidade = numero(resultado, "capacidade_nuvem");
    const atendidos = numero(resultado, "clientes_atendidos");
    if (naoAtendidos > 0) return "vermelho";
    if (capacidade != null && atendidos != null && atendidos / capacidade > 0.9) return "amarelo";
    return capacidade != null ? "verde" : "neutro";
  }
  const otif = numero(resultado, "otif");
  const refugo = dividir(numero(resultado, "refugo"), numero(resultado, "producao_real"));
  const ruptura = numero(resultado, "ruptura") ?? 0;
  if (otif == null || refugo == null) return "neutro";
  if (ruptura > 0 || (otif != null && otif < 0.75)) return "vermelho";
  if (otif <= 0.9 || refugo >= 0.03) return "amarelo";
  return "verde";
}

function CartaoDepartamento({ titulo, estado, metricas }: { titulo: string; estado: Semaforo; metricas: Metrica[] }) {
  return <article className={`rounded-xl border p-3 ${cor[estado]}`}>
    <header className="mb-2 flex items-center justify-between gap-2"><h3 className="font-semibold text-slate-900">{titulo}</h3><span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-700"><i aria-hidden className={`h-2.5 w-2.5 rounded-full ${ponto[estado]}`} />{nomeCor[estado]}</span></header>
    <dl className="space-y-2">{metricas.slice(0, 4).map((item) => <div key={item.nome} className="flex items-start justify-between gap-3 border-t border-slate-200/70 pt-2 first:border-0 first:pt-0"><dt className="text-xs text-slate-600"><abbr className="cursor-help no-underline decoration-dotted underline-offset-2" title={item.ajuda}>{item.nome}</abbr></dt><dd className="text-right text-xs font-semibold text-slate-800"><span className="block tabular-nums">{unidade(item.valor, item.formato)}</span><span className="font-normal text-slate-500">{delta(item.valor, item.anterior, item.formato)}</span></dd></div>)}</dl>
  </article>;
}

function macroValor(item: BoletimItem | undefined) {
  if (!item) return "N/D";
  const encontrado = item.resumo.match(/\d{1,3}(?:[.,]\d{1,2})?%/);
  return encontrado?.[0] ?? item.competencia ?? "Confirmado";
}

export default function CockpitDecisao({ empresaId, empresa, turma, resultados, decisao, aoConferir }: {
  empresaId: number; empresa: Empresa; turma: Turma; resultados: Resultado[]; decisao: Decisao | null; aoConferir: () => void;
}) {
  const [boletim, setBoletim] = useState<Boletim | null>(null);
  const atual = resultados[resultados.length - 1];
  const anterior = resultados.length > 1 ? resultados[resultados.length - 2] : undefined;
  const modo = (atual?.detalhes_simulacao?.modo ?? turma.modo_jogo) as ModoJogo;
  useEffect(() => { let ativo = true; api.get<Boletim>(`/api/aluno/empresas/${empresaId}/atualizacoes-oficiais`).then((dados) => { if (ativo) setBoletim(dados); }).catch(() => { if (ativo) setBoletim(null); }); return () => { ativo = false; }; }, [empresaId]);

  const dados = useMemo(() => {
    if (!atual) return [] as { titulo: string; estado: Semaforo; metricas: Metrica[] }[];
    const receitaPorFuncionario = dividir(atual.dre.receita, atual.funcionarios);
    const receitaPorFuncionarioAnterior = dividir(anterior?.dre.receita, anterior?.funcionarios);
    const custoUnitario = dividir(atual.dre.cmv, atual.unidades_vendidas);
    const custoUnitarioAnterior = dividir(anterior?.dre.cmv, anterior?.unidades_vendidas);
    const qualidade = atual.qualidade;
    const qualidadeAnterior = anterior?.qualidade ?? null;
    const moral = numero(atual, "moral");
    const moralAnterior = numero(anterior, "moral");
    const margem = dividir(atual.dre.lucro_liquido, atual.dre.receita);
    const margemAnterior = dividir(anterior?.dre.lucro_liquido, anterior?.dre.receita);
    const liquidez = numero(atual, "liquidez_corrente");
    const liquidezAnterior = numero(anterior, "liquidez_corrente");
    const custoLogistico = dividir((atual.dre.frete ?? 0) + (atual.dre.armazenagem ?? 0), atual.dre.receita);
    const custoLogisticoAnterior = dividir((anterior?.dre.frete ?? 0) + (anterior?.dre.armazenagem ?? 0), anterior?.dre.receita);
    const crescimento = dividir(atual.dre.receita - (anterior?.dre.receita ?? 0), anterior?.dre.receita);
    const usoNuvem = dividir(numero(atual, "clientes_atendidos"), numero(atual, "capacidade_nuvem"));
    const usoNuvemAnterior = dividir(numero(anterior, "clientes_atendidos"), numero(anterior, "capacidade_nuvem"));
    const refugo = dividir(numero(atual, "refugo"), numero(atual, "producao_real"));
    const refugoAnterior = dividir(numero(anterior, "refugo"), numero(anterior, "producao_real"));
    const giroEstoque = dividir(atual.dre.cmv, atual.detalhes_simulacao?.estado_final?.estoque_pa?.valor ?? null);
    const giroEstoqueAnterior = dividir(anterior?.dre.cmv, anterior?.detalhes_simulacao?.estado_final?.estoque_pa?.valor ?? null);
    const roi = atual.dre.marketing > 0 ? dividir(atual.dre.receita - atual.dre.marketing, atual.dre.marketing) : null;
    const roiAnterior = anterior?.dre.marketing && anterior.dre.marketing > 0 ? dividir(anterior.dre.receita - anterior.dre.marketing, anterior.dre.marketing) : null;
    const investimentoPd = dividir(atual.dre.pd, atual.dre.receita);
    const investimentoPdAnterior = dividir(anterior?.dre.pd, anterior?.dre.receita);
    const cartoes = [
      { titulo: "Produtos e marketing", estado: atual.participacao_mercado > 0 ? "verde" as Semaforo : "amarelo" as Semaforo, metricas: [
        metrica("Participação de mercado", "Parcela das vendas da empresa no mercado simulado. Uma queda reduz poder competitivo.", atual.participacao_mercado, anterior?.participacao_mercado ?? null, "percentual"),
        metrica("ROI de campanhas", "Comparação didática entre receita semanal e gasto de marketing; não prova causalidade da campanha.", roi, roiAnterior, "numero"),
        modo === "STARTUP" ? metrica("CAC", "Custo de aquisição por cliente. Se aumenta, cada novo cliente consome mais caixa.", numero(atual, "cac"), numero(anterior, "cac"), "moeda") : metrica("Ticket médio", "Receita média por unidade vendida. Quedas podem exigir revisão de preço e mix.", dividir(atual.dre.receita, atual.unidades_vendidas), dividir(anterior?.dre.receita, anterior?.unidades_vendidas), "moeda"),
        modo === "STARTUP" ? metrica("LTV", "Valor econômico estimado do cliente durante o relacionamento. Se fica abaixo do CAC, a aquisição tende a destruir valor.", numero(atual, "ltv"), numero(anterior, "ltv"), "moeda") : metrica("Elasticidade de preço", "Exige série de preço e demanda por produto. O motor ainda não registra base suficiente para calcular com segurança.", null, null, "numero"),
      ]},
      { titulo: "P&D e inovação", estado: investimentoPd == null ? "neutro" as Semaforo : investimentoPd > 0.25 ? "amarelo" as Semaforo : "verde" as Semaforo, metricas: [
        metrica("Qualidade do produto", "Nível de qualidade gerado pelo motor. Ajuda a sustentar demanda e satisfação.", qualidade, qualidadeAnterior, "numero"),
        metrica("Receita investida", "Parcela da receita semanal aplicada em pesquisa e desenvolvimento.", investimentoPd, investimentoPdAnterior, "percentual"),
        modo === "TRADICIONAL" ? metrica("Custo unitário", "CMV dividido pelas unidades vendidas. Quedas sustentáveis preservam margem.", custoUnitario, custoUnitarioAnterior, "moeda") : metrica("Adoção de recursos", "Ainda não há registro suficiente de adoção por funcionalidade no motor digital.", null, null, "percentual"),
        modo === "TRADICIONAL" ? metrica("Vida útil do produto", "A vida útil do produto ainda não é registrada separadamente da vida útil das máquinas.", null, null, "semanas") : metrica("Time-to-market", "O motor ainda não registra o tempo entre desenvolvimento e lançamento por recurso.", null, null, "semanas"),
      ]},
      { titulo: "Recursos humanos", estado: grauRh(atual), metricas: [
        metrica("Produtividade média", "Receita semanal por colaborador. Compare com a evolução da equipe, não isoladamente.", receitaPorFuncionario, receitaPorFuncionarioAnterior, "moeda"),
        metrica("Moral da equipe", "Índice de clima calculado pelas decisões de remuneração, benefícios, treinamento e sobrecarga. Escala de 0 a 100.", moral, moralAnterior, "escala"),
        modo === "STARTUP" ? metrica("Turnover", "Saídas da equipe na semana. Aumentos elevam custo de reposição e perda de conhecimento.", numero(atual, "turnover"), numero(anterior, "turnover"), "numero") : metrica("Horas extras", "Horas extras planejadas por colaborador. Excesso aumenta sobrecarga e custos.", numero(atual, "horas_extras"), numero(anterior, "horas_extras"), "numero"),
        modo === "STARTUP" ? metrica("Receita por colaborador", "Receita semanal dividida pela equipe ativa. Compare com a qualidade e a retenção.", receitaPorFuncionario, receitaPorFuncionarioAnterior, "moeda") : metrica("Custo de treinamento", "Gasto semanal em capacitação. Deve ser interpretado junto com qualificação e produtividade.", atual.dre.treinamento ?? null, anterior?.dre.treinamento ?? null, "moeda"),
      ]},
      { titulo: "Estratégia", estado: crescimento == null ? "neutro" as Semaforo : crescimento < -0.15 ? "vermelho" as Semaforo : crescimento < 0 ? "amarelo" as Semaforo : "verde" as Semaforo, metricas: [
        metrica("Crescimento semanal", "Variação da receita em relação à semana anterior. Mostra tendência, não garante causalidade.", crescimento, null, "percentual"),
        metrica("Posição BCG", "A classificação BCG exige crescimento de mercado e participação relativa por produto; dados ainda não registrados.", null, null, "numero"),
        metrica("Risco PESTEL", "A análise PESTEL é qualitativa e deve ser registrada pela equipe; não recebe uma nota automática.", null, null, "numero"),
        modo === "STARTUP" ? metrica("Vantagem digital", "A vantagem competitiva digital exige medida por recurso, canal ou tecnologia, ainda não registrada isoladamente.", null, null, "numero") : metrica("Poder de fornecedores", "Exige a avaliação estruturada das Cinco Forças. Não deve ser deduzido apenas dos custos da semana.", null, null, "numero"),
      ]},
      { titulo: "Finanças", estado: grauFinancas(atual, empresa), metricas: [
        metrica("Margem líquida", "Lucro ou prejuízo final como proporção da receita da semana.", margem, margemAnterior, "percentual"),
        metrica("Liquidez corrente", "Ativos de curto prazo divididos por obrigações de curto prazo. Quedas reduzem a folga de pagamento.", liquidez, liquidezAnterior, "numero"),
        modo === "STARTUP" ? metrica("Burn rate", "Queima operacional de caixa por semana. Aumentos reduzem a autonomia financeira.", numero(atual, "burn"), numero(anterior, "burn"), "moeda") : metrica("EBITDA operacional", "Resultado antes de juros, impostos, depreciação e amortização, quando o motor possui todos os dados.", numero(atual, "ebitda"), numero(anterior, "ebitda"), "moeda"),
        modo === "STARTUP" ? metrica("Runway", "Semanas de caixa disponíveis mantendo a queima operacional atual.", numero(atual, "runway"), numero(anterior, "runway"), "semanas") : metrica("Giro do imobilizado", "Receita semanal em relação ao valor líquido das máquinas. Mede o uso econômico dos ativos físicos.", dividir(atual.dre.receita, atual.detalhes_simulacao?.balanco?.imobilizado ?? null), dividir(anterior?.dre.receita, anterior?.detalhes_simulacao?.balanco?.imobilizado ?? null), "numero"),
      ]},
      { titulo: "Produção e operação", estado: grauOperacao(atual, modo), metricas: [
        metrica("Custo unitário", "CMV por unidade vendida. Uma alta sem reajuste de preço pressiona a margem.", custoUnitario, custoUnitarioAnterior, "moeda"),
        modo === "STARTUP" ? metrica("Uso da nuvem", "Clientes atendidos em relação à capacidade contratada. Próximo do limite aumenta o risco de indisponibilidade.", usoNuvem, usoNuvemAnterior, "percentual") : metrica("Ocupação da fábrica", "Produção realizada em relação à capacidade disponível das máquinas.", numero(atual, "utilizacao_maquinas"), numero(anterior, "utilizacao_maquinas"), "percentual"),
        modo === "STARTUP" ? metrica("Clientes não atendidos", "Clientes que não puderam ser atendidos por capacidade insuficiente na semana.", numero(atual, "clientes_nao_atendidos"), numero(anterior, "clientes_nao_atendidos"), "numero") : metrica("Refugo", "Percentual da produção que não ficou aproveitável. Aumento gera desperdício e risco de falta de estoque.", refugo, refugoAnterior, "percentual"),
        modo === "STARTUP" ? metrica("Custo por usuário", "O custo de servidor por usuário ainda não é lançado isoladamente na DRE do modo digital.", null, null, "moeda") : metrica("OEE", "Disponibilidade, performance e qualidade da operação. Quedas sinalizam perda de eficiência produtiva.", numero(atual, "oee"), numero(anterior, "oee"), "percentual"),
      ]},
      { titulo: "Logística e entregas", estado: grauOperacao(atual, modo), metricas: [
        metrica("Nível de serviço (OTIF)", "Pedidos entregues no prazo e completos. Quedas afetam satisfação e recompra.", numero(atual, "otif"), numero(anterior, "otif"), "percentual"),
        metrica("Custo logístico / receita", "Frete e armazenagem registrados como parcela da receita semanal.", custoLogistico, custoLogisticoAnterior, "percentual"),
        modo === "STARTUP" ? metrica("Churn", "Percentual de clientes perdidos na base; alta recorrente reduz receita futura.", numero(atual, "churn"), numero(anterior, "churn"), "percentual") : metrica("Giro de estoque", "CMV semanal em relação ao estoque final de produtos acabados. Interprete junto com risco de ruptura.", giroEstoque, giroEstoqueAnterior, "numero"),
        modo === "STARTUP" ? metrica("Ativação digital", "O tempo de ativação por cliente ainda não é registrado separadamente pelo motor.", null, null, "semanas") : metrica("Frete e armazenagem", "Custo logístico registrado na DRE. Altas pressionam preço e margem.", (atual.dre.frete ?? 0) + (atual.dre.armazenagem ?? 0), (anterior?.dre.frete ?? 0) + (anterior?.dre.armazenagem ?? 0), "moeda"),
      ]},
    ];
    return cartoes;
  }, [atual, anterior, empresa, modo]);

  const alertas = useMemo(() => {
    if (!atual) return [] as { nivel: "amarelo" | "vermelho"; texto: string }[];
    const lista: { nivel: "amarelo" | "vermelho"; texto: string }[] = [];
    const producaoPlanejada = decisao?.simulacao?.producao ?? 0;
    const estoquePronto = empresa.estado_simulacao?.estoque_pa.quantidade ?? 0;
    if (modo === "TRADICIONAL" && atual.demanda > estoquePronto + producaoPlanejada) lista.push({ nivel: "vermelho", texto: "Ruptura de estoque iminente: a demanda da última semana supera o estoque pronto somado à produção planejada." });
    if ((decisao?.pd ?? 0) > Math.max(0, empresa.caixa) * 0.25) lista.push({ nivel: "amarelo", texto: "Risco de caixa: o investimento em P&D supera 25% do caixa disponível e pode comprometer o capital de giro." });
    const extras = decisao?.simulacao?.horas_extras ?? 0;
    if (modo === "TRADICIONAL" && (extras > 10 || (numero(atual, "ruptura") ?? 0) > 0)) lista.push({ nivel: "amarelo", texto: "Gargalo de equipe: horas extras elevadas ou ruptura recente podem reduzir a entrega e aumentar o risco de saídas." });
    return lista;
  }, [atual, decisao, empresa, modo]);

  const setor = turma.parametros?.configuracao_simulacao?.setor_mercado ?? turma.configuracao_simulacao?.setor_mercado;
  const selic = boletim?.itens.find((item) => /selic/i.test(`${item.titulo} ${item.resumo}`));
  const ipca = boletim?.itens.find((item) => /ipca|infla[cç][aã]o/i.test(`${item.titulo} ${item.resumo}`));
  const setorItem = boletim?.itens.find((item) => setor && item.setores_afetados?.includes(setor));

  return <section aria-label="Cockpit de decisão">
    <header className="mb-4"><h2 className="text-xl font-bold text-corporativo">Cockpit de decisão</h2><p className="mt-1 text-sm text-slate-600">Leitura da última semana fechada e checagem do rascunho atual antes de enviar.</p></header>
    {!atual ? <div className="rounded-xl border border-cyan-200 bg-cyan-50 p-4 text-sm">O cockpit será preenchido após o fechamento da primeira semana. Enquanto isso, consulte o mercado e prepare as decisões.</div> : <>
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Termômetro macro e caixa">
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-3"><p className="text-xs text-slate-600">Caixa disponível</p><p className="mt-1 text-xl font-bold text-corporativo">{reais(empresa.caixa)}</p><p className="text-xs text-slate-500">{unidade(Math.max(0, empresa.caixa) / Math.max(1, atual.dre.custos_fixos + atual.dre.folha), "semanas")} de custos fixos e folha</p></div>
        <div className="rounded-xl border border-slate-200 bg-white p-3"><p className="text-xs text-slate-600">Resultado líquido · última semana</p><p className={`mt-1 text-xl font-bold ${atual.dre.lucro_liquido < 0 ? "valor-negativo" : "text-emerald-700"}`}>{reais(atual.dre.lucro_liquido)}</p><p className="text-xs text-slate-500">{delta(atual.dre.lucro_liquido, anterior?.dre.lucro_liquido ?? null, "moeda")}</p></div>
        <div className="rounded-xl border border-slate-200 bg-white p-3"><p className="text-xs text-slate-600">Selic · fonte oficial</p><p className="mt-1 text-xl font-bold text-slate-800">{macroValor(selic)}</p><p className="truncate text-xs text-slate-500" title={selic?.referencia}>{selic?.competencia ?? selic?.referencia ?? "N/D"}</p></div>
        <div className="rounded-xl border border-slate-200 bg-white p-3"><p className="text-xs text-slate-600">IPCA / setor · fonte oficial</p><p className="mt-1 text-xl font-bold text-slate-800">{macroValor(ipca ?? setorItem)}</p><p className="truncate text-xs text-slate-500" title={(ipca ?? setorItem)?.titulo}>{(ipca ?? setorItem)?.competencia ?? (ipca ?? setorItem)?.titulo ?? "N/D"}</p></div>
      </section>
      <section className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3" aria-label="Indicadores dos departamentos">{dados.map((cartao) => <CartaoDepartamento key={cartao.titulo} {...cartao} />)}</section>
      <section className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3" aria-label="Radar de conferência">
        <div className="flex flex-wrap items-center justify-between gap-2"><div><h3 className="font-semibold text-slate-900">Radar de conferência</h3><p className="text-xs text-slate-600">Validação cruzada do rascunho antes do envio definitivo.</p></div><button type="button" className="rounded-lg bg-marinho px-3 py-2 text-sm font-semibold text-white" onClick={aoConferir}>Conferir e enviar →</button></div>
        {alertas.length === 0 ? <p className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-2 text-sm text-emerald-900">Nenhum gargalo crítico foi identificado com os dados registrados. Revise também as decisões e o cenário de mercado.</p> : <ul className="mt-3 space-y-2">{alertas.map((alerta) => <li key={alerta.texto} className={`rounded-lg border-l-4 p-2 text-sm ${alerta.nivel === "vermelho" ? "border-red-600 bg-red-50 text-red-900" : "border-amber-500 bg-amber-50 text-amber-900"}`}>{alerta.texto}</li>)}</ul>}
      </section>
    </>}
  </section>;
}
