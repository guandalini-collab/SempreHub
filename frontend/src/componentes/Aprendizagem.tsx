import ManualMidias from "./ManualMidias";
import { MercadoPublicado } from "./MercadoReal";
import React, { useEffect, useMemo, useState } from "react";

import { Botao, Cartao } from "./ui";
import { CatalogoCompleto } from "./ConteudoRodada";
import { api, sessaoSalva } from "../api";

type PerfilAprendizagem = "ALUNO" | "PROFESSOR";
type AbaBiblioteca = "REFERENCIAS" | "ANALISES" | "NEWS" | "MIDIAS";

interface EventoEducacional {
  titulo: string;
  resumo: string;
  impacto: string;
  acao: string;
  sinal: "Mercado" | "Operação" | "Finanças" | "Pessoas";
}

function chaveTour() { return `semprehub.tour.aprendizagem.v2.${sessaoSalva()?.id ?? "anonimo"}.${sessaoSalva()?.papel ?? "ALUNO"}`; }

const passosAluno = [
  {
    titulo: "1. Entenda a rodada",
    texto: "Leia o evento do mês e a edição do SempreHub News antes de preencher a decisão.",
  },
  {
    titulo: "2. Monte a decisão",
    texto: "Use a prévia para comparar preço, produção, marketing, pessoas, estoque e caixa.",
  },
  {
    titulo: "3. Registre e acompanhe",
    texto: "Salve a decisão, confirme com sua equipe e observe DRE, caixa, mercado e histórico.",
  },
];

const passosProfessor = [
  {
    titulo: "1. Prepare a turma",
    texto: "Defina o modo, o cenário, as rodadas e os parâmetros antes de divulgar o código de acesso.",
  },
  {
    titulo: "2. Conduza cada rodada",
    texto: "Acompanhe pendências, use os eventos e feche o mês somente depois de revisar as decisões.",
  },
  {
    titulo: "3. Faça a devolutiva",
    texto: "Compare resultados, abra os relatórios e conecte as escolhas às análises de mercado e finanças.",
  },
];

const referencias = [
  {
    autor: "José Dornelas",
    tema: "Comportamento empreendedor",
    onde: "Empreendedorismo: Transformando Ideias em Negócios — capítulos sobre perfil, oportunidade e plano de negócio.",
    uso: "Ajuda a interpretar GEM, classe de entrada e decisões de desenvolvimento da empresa.",
  },
  {
    autor: "Global Entrepreneurship Monitor (GEM)",
    tema: "Motivação para empreender",
    onde: "Relatórios GEM — seções de empreendedorismo por necessidade e por oportunidade.",
    uso: "Diferencia o motivo inicial do negócio e orienta a leitura da trajetória empreendedora.",
  },
  {
    autor: "Michael Porter",
    tema: "Estratégia e concorrência",
    onde: "Competitive Strategy — capítulo sobre as cinco forças competitivas.",
    uso: "Organiza a análise do setor antes de escolher preço, posicionamento e canais.",
  },
  {
    autor: "Philip Kotler e Kevin Lane Keller",
    tema: "Marketing e segmentação",
    onde: "Administração de Marketing — capítulos de análise de mercado, segmentação e composto de marketing.",
    uso: "Relaciona público, proposta de valor, mídia, preço e comunicação.",
  },
  {
    autor: "Francis J. Aguilar",
    tema: "Ambiente externo",
    onde: "Scanning the Business Environment — matriz PESTEL e leitura do macroambiente.",
    uso: "Ajuda a separar fatores externos que a empresa observa daqueles que consegue controlar.",
  },
  {
    autor: "Kaplan e Norton",
    tema: "Indicadores e execução",
    onde: "The Balanced Scorecard — capítulos sobre objetivos, indicadores e aprendizagem.",
    uso: "Conecta indicadores financeiros, mercado, operação e pessoas na discussão do resultado.",
  },
];

const porter = [
  ["Rivalidade entre concorrentes", "Preço, qualidade, campanhas e velocidade de resposta na disputa atual."],
  ["Novos entrantes", "Barreiras de capital, tecnologia, marca, distribuição e regulação."],
  ["Fornecedores", "Dependência, concentração, prazos e capacidade de repassar custos."],
  ["Clientes", "Sensibilidade a preço, alternativas disponíveis e poder de negociação."],
  ["Substitutos", "Outras soluções que resolvem o mesmo problema do cliente."],
] as const;

const pestel = [
  ["Político", "Políticas públicas, estabilidade, subsídios e prioridades governamentais."],
  ["Econômico", "Juros, inflação, emprego, crédito e poder de compra."],
  ["Social", "Demografia, hábitos, cultura, valores e mudanças de comportamento."],
  ["Tecnológico", "Automação, inteligência artificial, plataformas e inovação."],
  ["Ecológico", "Clima, recursos, resíduos, energia e sustentabilidade."],
  ["Legal", "Tributos, trabalho, LGPD, consumidor e normas do setor."],
] as const;

const segmentacoes = [
  ["Demográfica", "Idade, renda, escolaridade, profissão e tamanho da família."],
  ["Geográfica", "País, estado, cidade, bairro, clima e densidade urbana ou rural."],
  ["Psicográfica", "Estilo de vida, valores, personalidade e aspirações."],
  ["Comportamental", "Frequência de compra, lealdade e benefícios procurados."],
] as const;

const noticiasBase: EventoEducacional[] = [
  {
    titulo: "Custo do dinheiro em observação",
    resumo: "Juros mais altos tornam empréstimos e capital de giro mais caros.",
    impacto: "Uma dívida maior pode reduzir o caixa das próximas rodadas.",
    acao: "Compare o custo do crédito com a margem e preserve uma reserva de caixa.",
    sinal: "Finanças",
  },
  {
    titulo: "Cliente mais sensível ao valor",
    resumo: "Quando o orçamento aperta, preço e benefício percebido pesam mais na escolha.",
    impacto: "Posicionamento desalinhado pode reduzir demanda e participação.",
    acao: "Revise público, proposta de valor, canal e preço antes de aumentar a produção.",
    sinal: "Mercado",
  },
  {
    titulo: "Prazo de entrega afeta a experiência",
    resumo: "Modalidades rápidas custam mais; modalidades econômicas exigem planejamento.",
    impacto: "A escolha logística aparece na satisfação do cliente da rodada seguinte.",
    acao: "Escolha o prazo considerando estoque, caixa e promessa feita ao mercado.",
    sinal: "Operação",
  },
  {
    titulo: "Capacidade depende das pessoas",
    resumo: "Treinamento, remuneração e carga de trabalho influenciam produtividade e retenção.",
    impacto: "Economizar no desenvolvimento pode criar retrabalho e turnover.",
    acao: "Leia o indicador de pessoas junto com capacidade, qualidade e caixa.",
    sinal: "Pessoas",
  },
];

const midias = [
  ["Meta Ads", "Anúncios segmentados em Instagram e Facebook; compra por impressão ou clique para gerar alcance e ação."],
  ["Google Ads", "Anúncios em buscas e sites parceiros; captura pessoas que já pesquisam uma solução."],
  ["YouTube Ads", "Vídeos e banners na plataforma; explica a proposta e amplia lembrança de marca."],
  ["TikTok Ads", "Vídeos curtos distribuídos por interesse; experimenta mensagens e alcance com frequência."],
  ["LinkedIn Ads", "Mídia voltada a contexto profissional; divulga conteúdo, evento ou oferta para audiência corporativa."],
  ["Mídia programática", "Banners comprados em leilões automatizados; amplia presença em portais e aplicativos."],
  ["WhatsApp, SMS e push", "Mensagens diretas por API; ativa relacionamento, lembrete e comunicação de ofertas."],
  ["TV aberta ou por assinatura", "Inserções audiovisuais; constrói alcance e reconhecimento em períodos definidos."],
  ["Rádio", "Spots de áudio em emissoras; repete uma mensagem e alcança ouvintes de uma região."],
  ["Jornais e revistas", "Espaços editoriais ou anúncios impressos; comunica uma mensagem em publicação e edição específicas."],
  ["Outdoor e painel de LED", "Mídia exterior em pontos de circulação; gera visibilidade durante um período ou cota."],
  ["Busdoor e mobiliário urbano", "Peças em veículos ou equipamentos públicos; mantém a marca em trajetos e locais de passagem."],
  ["Telas corporativas e elevadores", "Inserções em circuitos internos; alcança pessoas durante sua permanência no ambiente."],
  ["Streaming de áudio", "Anúncios entre conteúdos musicais; combina mensagem de áudio e, quando disponível, banner clicável."],
  ["Podcasts e cinema", "Patrocínio, testemunhal ou vídeo antes da sessão; associa a marca ao contexto do conteúdo."],
  ["Influência e eventos", "Conteúdo de criadores, feiras e parcerias; produz prova social e interação com a audiência."],
  ["Panfletagem e materiais de PDV", "Peças físicas e abordagem local; informa, orienta a compra e reforça a presença no ponto de venda."],
] as const;

function lerTourConcluido() {
  try {
    return window.localStorage.getItem(chaveTour()) === "sim";
  } catch {
    return false;
  }
}

function salvarTourConcluido(valor: boolean) {
  try {
    if (valor) window.localStorage.setItem(chaveTour(), "sim");
    else window.localStorage.removeItem(chaveTour());
  } catch {
    /* O tour continua disponível quando o navegador bloqueia armazenamento. */
  }
}

export function TourGuiado({ perfil }: { perfil: PerfilAprendizagem }) {
  const [fechado, setFechado] = useState(lerTourConcluido);
  const [naoMostrar, setNaoMostrar] = useState(false);
  const [passoAtual, setPassoAtual] = useState(0);
  const passos = perfil === "ALUNO" ? passosAluno : passosProfessor;

  useEffect(() => {
    setFechado(lerTourConcluido());
  }, [perfil]);

  if (fechado) {
    return (
      <button
        type="button"
        onClick={() => {
          salvarTourConcluido(false);
          setFechado(false);
        }}
        className="text-left text-xs font-semibold text-marinho underline decoration-ouro underline-offset-4"
      >
        Reabrir orientação inicial
      </button>
    );
  }

  return (
    <Cartao
      titulo={perfil === "ALUNO" ? "Primeiros passos do aluno" : "Primeiros passos do professor"}
      acao={<span className="rounded-full bg-ouro/15 px-2.5 py-1 text-xs font-semibold text-marinho">Guia rápido</span>}
      className="border-l-4 border-ouro"
    >
      <div className="grid gap-3 md:grid-cols-3">
        {passos.slice(passoAtual, passoAtual + 1).map((passo) => (
          <div key={passo.titulo} className="rounded-lg bg-slate-50 p-3">
            <h3 className="text-sm font-semibold text-marinho">{passo.titulo}</h3>
            <p className="mt-1 text-xs leading-relaxed text-slate-600">{passo.texto}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3">
        {passoAtual === passos.length - 1 && <label className="flex items-center gap-2 text-xs text-slate-600">
          <input type="checkbox" checked={naoMostrar} onChange={(e) => setNaoMostrar(e.target.checked)} className="h-4 w-4 accent-[#FFC233]" />
          Não mostrar novamente
        </label>}
        {passoAtual > 0 && <Botao variante="secundario" onClick={() => setPassoAtual(passoAtual - 1)}>Anterior</Botao>}
        <Botao
          type="button"
          variante="secundario"
          onClick={() => {
            if (passoAtual < passos.length - 1) { setPassoAtual(passoAtual + 1); return; }
            if (naoMostrar) salvarTourConcluido(true);
            setFechado(true);
          }}
        >
          {passoAtual < passos.length - 1 ? "Próximo" : "Entendi, começar"}
        </Botao>
      </div>
    </Cartao>
  );
}

export function BibliotecaAprendizagem({ rodada, modo, empresaId, mercadoSeparado = false }: { rodada?: number; modo?: string; empresaId?: number; mercadoSeparado?: boolean }) {
  const [aba, setAba] = useState<AbaBiblioteca>(mercadoSeparado ? "REFERENCIAS" : "NEWS");
  const noticias = useMemo(() => {
    if (!rodada) return noticiasBase;
    return noticiasBase.map((noticia) => ({ ...noticia, titulo: `Rodada ${rodada}: ${noticia.titulo}` }));
  }, [rodada]);

  const abas: { id: AbaBiblioteca; titulo: string }[] = [
    ...(!mercadoSeparado ? [{ id: "NEWS" as const, titulo: "SempreHub News" }] : []),
    { id: "REFERENCIAS", titulo: "Autores e referências" },
    { id: "ANALISES", titulo: "Análises" },
    { id: "MIDIAS", titulo: "Mídias e comunicação" },
  ];

  return (
    <Cartao
      titulo="Biblioteca de aprendizagem"
      acao={<span className="text-xs text-slate-500">Consulte antes de decidir</span>}
    >
      <p className="mb-4 max-w-3xl text-sm leading-relaxed text-slate-600">
        Use este material para justificar escolhas da simulação. As referências ajudam a formular hipóteses; os indicadores da sua empresa mostram o efeito de cada decisão.
        {modo === "STARTUP" ? " Em uma startup, observe também aquisição, retenção e capacidade de atendimento." : " Em uma empresa tradicional, conecte mercado, operação, estoque e caixa."}
      </p>
      <div className="-mx-1 mb-5 flex gap-1 overflow-x-auto px-1 pb-1" role="tablist" aria-label="Biblioteca de aprendizagem">
        {abas.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={aba === item.id}
            onClick={() => setAba(item.id)}
            className={`shrink-0 rounded-lg px-3 py-2 text-xs font-semibold transition ${aba === item.id ? "bg-marinho text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
          >
            {item.titulo}
          </button>
        ))}
      </div>

      {aba === "NEWS" && (empresaId ? <MercadoPublicado empresaId={empresaId} rodada={rodada ?? 1}/> : <p className="text-sm">Abra o painel da empresa para ler as edições do SempreHub News com os eventos e indicadores reais de mercado.</p>)}
      {aba === "REFERENCIAS" && <Referencias />}
      {aba === "ANALISES" && <Analises />}
      {aba === "MIDIAS" && <ManualMidias />}
    </Cartao>
  );
}

function SempreHubNews({ noticias }: { noticias: EventoEducacional[] }) {
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2 border-b border-slate-100 pb-3">
        <div>
          <p className="text-lg font-bold text-marinho">SempreHub News</p>
          <p className="text-xs text-slate-500">Boletim interno para leitura da rodada</p>
        </div>
        <span className="text-xs text-slate-400">Sinais educacionais · não é cotação em tempo real</span>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {noticias.map((noticia) => (
          <article key={noticia.titulo} className="rounded-lg border border-slate-200 p-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="rounded-full bg-ouro/15 px-2 py-0.5 text-[11px] font-semibold text-marinho">{noticia.sinal}</span>
              <span className="text-[11px] uppercase tracking-wide text-slate-400">Análise</span>
            </div>
            <h3 className="text-sm font-semibold text-marinho">{noticia.titulo}</h3>
            <p className="mt-1 text-xs leading-relaxed text-slate-600">{noticia.resumo}</p>
            <dl className="mt-3 space-y-2 text-xs">
              <div><dt className="font-semibold text-slate-700">Possível impacto</dt><dd className="text-slate-600">{noticia.impacto}</dd></div>
              <div><dt className="font-semibold text-slate-700">Pergunta para a equipe</dt><dd className="text-slate-600">{noticia.acao}</dd></div>
            </dl>
          </article>
        ))}
      </div>
    </div>
  );
}

function Referencias() {
  const [fontes, setFontes] = useState<{id:string;autor:string;obra:string;localizacao:string;contribuicao:string;nota_edicao:string}[]>([]);
  const [erro, setErro] = useState("");
  useEffect(() => { api.get<{referencias:typeof fontes}>("/api/educacao/referencias").then(r => setFontes(r.referencias)).catch(e => setErro(e.message)); }, []);
  return (
    <div className="space-y-3">
      <p className="text-xs leading-relaxed text-slate-500">Os autores abaixo são referências para estudo e discussão. Consulte a edição disponível na sua instituição; a plataforma não substitui a leitura das obras.</p>
      <div className="grid gap-3 md:grid-cols-2">
        {erro && <p role="alert">{erro}</p>}
        {fontes.map((item) => (
          <article key={item.autor} className="rounded-lg border border-slate-200 p-4">
            <p className="text-sm font-semibold text-marinho">{item.autor}</p>
            <p className="mt-1 text-xs font-semibold text-ouro">{item.obra}</p>
            <p className="mt-2 text-xs leading-relaxed text-slate-600"><strong>Onde buscar:</strong> {item.localizacao}</p>
            <p className="mt-2 text-xs leading-relaxed text-slate-600"><strong>Na simulação:</strong> {item.contribuicao}</p>
            <p className="mt-2 text-xs text-slate-500">{item.nota_edicao}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function Analises() {
  return (
    <div className="space-y-3">
      <p className="text-xs leading-relaxed text-slate-500">Comece pelo ambiente e pelo setor, transforme achados em hipóteses e só então registre a decisão. Não existe uma resposta única: explique o raciocínio da equipe.</p>
      <div className="grid gap-3 lg:grid-cols-2">
        <details open className="rounded-lg border border-slate-200 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-marinho">5 Forças de Porter · concorrência</summary>
          <div className="mt-3 space-y-2">{porter.map(([titulo, texto]) => <ItemAnalise key={titulo} titulo={titulo} texto={texto} />)}</div>
        </details>
        <details className="rounded-lg border border-slate-200 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-marinho">PESTEL · macroambiente</summary>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">{pestel.map(([titulo, texto]) => <ItemAnalise key={titulo} titulo={titulo} texto={texto} />)}</div>
        </details>
        <details className="rounded-lg border border-slate-200 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-marinho">Análise de mercado</summary>
          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            <ItemAnalise titulo="Público-alvo" texto="Quem compra, qual problema resolve e qual valor percebe." />
            <ItemAnalise titulo="Concorrência" texto="Alternativas diretas e indiretas, pontos fortes e fracos." />
            <ItemAnalise titulo="Tendências" texto="Mudanças de hábitos, tecnologia, renda e regras do setor." />
          </div>
        </details>
        <details className="rounded-lg border border-slate-200 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-marinho">SWOT (FOFA)</summary>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <ItemAnalise titulo="Forças" texto="Vantagens internas que a empresa consegue sustentar." />
            <ItemAnalise titulo="Fraquezas" texto="Limitações internas que precisam de melhoria." />
            <ItemAnalise titulo="Oportunidades" texto="Condições externas favoráveis ao crescimento." />
            <ItemAnalise titulo="Ameaças" texto="Riscos externos, crises e movimentos de rivais." />
          </div>
        </details>
        <details className="rounded-lg border border-slate-200 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-marinho">Análise financeira</summary>
          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            <ItemAnalise titulo="Viabilidade" texto="Projete custos, receita, margem e retorno do investimento." />
            <ItemAnalise titulo="Indicadores" texto="Acompanhe faturamento, lucro, caixa, dívida e capital de giro." />
            <ItemAnalise titulo="Riscos" texto="Teste perdas, crédito e reserva antes de comprometer o caixa." />
          </div>
        </details>
        <details className="rounded-lg border border-slate-200 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-marinho">Segmentação de mercado</summary>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">{segmentacoes.map(([titulo, texto]) => <ItemAnalise key={titulo} titulo={titulo} texto={texto} />)}</div>
          <p className="mt-3 text-xs leading-relaxed text-slate-500">Segmentar ajuda a reduzir desperdício de marketing, escolher canais, ajustar preço e encontrar nichos.</p>
        </details>
      </div>
    </div>
  );
}

function ItemAnalise({ titulo, texto }: { titulo: string; texto: string }) {
  return <div className="rounded-md bg-slate-50 p-2.5"><p className="text-xs font-semibold text-slate-700">{titulo}</p><p className="mt-0.5 text-xs leading-relaxed text-slate-600">{texto}</p></div>;
}

function CatalogoMidias() {
  const [filtro, setFiltro] = useState("");
  const itens = midias.filter(([nome, descricao]) => `${nome} ${descricao}`.toLocaleLowerCase().includes(filtro.toLocaleLowerCase()));
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-marinho">O que é cada mídia?</p>
          <p className="text-xs text-slate-500">A finalidade ajuda a comparar alternativas de comunicação na decisão.</p>
        </div>
        <label className="w-full sm:w-64">
          <span className="sr-only">Buscar mídia</span>
          <input className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-ouro focus:outline-none focus:ring-2 focus:ring-ouro/40" placeholder="Buscar canal ou finalidade" value={filtro} onChange={(e) => setFiltro(e.target.value)} />
        </label>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {itens.map(([nome, descricao]) => <article key={nome} className="rounded-lg border border-slate-200 p-3"><h3 className="text-xs font-semibold text-marinho">{nome}</h3><p className="mt-1 text-xs leading-relaxed text-slate-600">{descricao}</p></article>)}
      </div>
      {!itens.length && <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-500">Nenhuma mídia encontrada. Tente outro termo.</p>}
      <p className="mt-4 text-xs leading-relaxed text-slate-500">Custos, métricas e prazos são hipóteses didáticas e podem variar. Use a tabela de parâmetros da rodada para registrar a decisão financeira.</p>
    </div>
  );
}

export function ManualRapido({ perfil }: { perfil: PerfilAprendizagem }) {
  const [imprimindo, setImprimindo] = useState(false);
  const titulo = perfil === "ALUNO" ? "Manual rápido do aluno" : "Manual rápido do professor";
  const orientacoes = perfil === "ALUNO"
    ? ["Entre na turma e abra ou aceite uma empresa.", "Leia o evento e o SempreHub News.", "Preencha a decisão e use a prévia para conferir o impacto.", "Salve, confirme a versão e acompanhe o resultado da rodada."]
    : ["Crie a turma e escolha modo, cenário, parâmetros e número de rodadas.", "Acompanhe empresas, equipes e pendências antes do fechamento.", "Escolha o evento e feche uma rodada por vez.", "Use ranking, resultados e relatório para conduzir a devolutiva."];
  return (
    <Cartao titulo={titulo} acao={<a className="text-xs font-semibold text-marinho underline" href={`/manuais/manual-${perfil === "ALUNO" ? "aluno" : "professor"}.pdf`} target="_blank" rel="noreferrer">Abrir / baixar PDF ilustrado</a>}>
      <ol className="grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
        {orientacoes.map((texto, indice) => <li key={texto} className="flex gap-2 rounded-lg bg-slate-50 p-3"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-marinho text-xs font-bold text-white">{indice + 1}</span><span className="leading-relaxed">{texto}</span></li>)}
      </ol>
      <p className="mt-3 text-xs text-slate-500">O manual completo tem passo a passo, ilustrações e orientações para interpretar os resultados.</p>
    </Cartao>
  );
}
