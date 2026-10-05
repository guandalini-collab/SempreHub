export type Papel = "ALUNO" | "PROFESSOR";
export type RegimeTributario = "MEI" | "SIMPLES_NACIONAL" | "LUCRO_PRESUMIDO";
export type FaseAtual =
  | "IDEACAO"
  | "PLANEJAMENTO"
  | "CAPTACAO"
  | "OPERACAO_ESTAVEL"
  | "SOBREVIVENCIA";
export type TipoEntradaGem = "NECESSIDADE" | "OPORTUNIDADE";
export type ClasseDornelas = "SERIAL" | "FRANQUIA" | "CORPORATIVO" | "SOCIAL";

export interface Usuario {
  id: number;
  nome: string;
  email: string;
  papel: Papel;
  teste?: boolean;
}

export interface Parametros {
  total_rodadas: number;
  caixa_inicial: number;
  preco_referencia: number;
  custo_unitario: number;
  demanda_base_por_empresa: number;
  crescimento_mercado_mensal: number;
  produtividade_por_pessoa: number;
  custos_fixos_mensais: number;
  salario_base: number;
  taxa_juros_mensal: number;
  taxa_cheque_especial: number;
  limite_credito: number;
  probabilidade_evento: number;
  teto_mei_anual: number;
  das_mei_mensal: number;
  aliquota_icms: number;
}

export interface Turma {
  id: number;
  nome: string;
  codigo: string;
  status: "ABERTA" | "ENCERRADA";
  rodada_atual: number;
  total_rodadas: number;
  professor: string | null;
  quantidade_empresas: number;
  parametros?: Parametros;
  greve_rodadas_restantes?: number;
}

export interface Empresa {
  id: number;
  nome: string;
  aluno: string | null;
  aluno_id: number;
  aluno_email: string | null;
  tipo_entrada_gem: TipoEntradaGem;
  classe_dornelas: ClasseDornelas;
  regime_tributario: RegimeTributario;
  regime_pretendido: RegimeTributario | null;
  fase_atual: FaseAtual;
  caixa: number;
  divida: number;
  patrimonio: number;
  funcionarios: number;
  marca: number;
  qualidade: number;
  autoeficacia: number;
  necessidade_realizacao: number;
  networking: number;
  faturamento_ano: number;
  fator_clt: number;
  decisao_enviada?: boolean;
}

export interface Decisao {
  rodada: number;
  preco: number;
  marketing: number;
  pd: number;
  networking: number;
  contratar: number;
  demitir: number;
  emprestimo: number;
  amortizacao: number;
  regime_solicitado: RegimeTributario | null;
  automatica: boolean;
  enviada_em: string | null;
}

export type DecisaoEntrada = Omit<Decisao, "rodada" | "automatica" | "enviada_em">;

export interface PrevisaoDecisao {
  rodada: number;
  regime: RegimeTributario;
  funcionarios: number;
  capacidade: number;
  folha: number;
  juros: number;
  gastos_previstos: number;
  margem_unitaria: number;
  ponto_equilibrio: number | null;
  emprestimo_aprovado: number;
  amortizacao_aplicada: number;
  divida_prevista: number;
  caixa_disponivel: number;
  alertas: string[];
}

export interface Dre {
  receita: number;
  impostos: number;
  cmv: number;
  folha: number;
  custos_fixos: number;
  marketing: number;
  pd: number;
  networking: number;
  rescisoes: number;
  royalties: number;
  juros: number;
  multas: number;
  lucro_liquido: number;
}

export interface Resultado {
  rodada: number;
  preco: number;
  demanda: number;
  capacidade: number;
  unidades_vendidas: number;
  participacao_mercado: number;
  dre: Dre;
  caixa_final: number;
  divida_final: number;
  regime: RegimeTributario;
  aliquota_efetiva: number;
  funcionarios: number;
  marca: number;
  qualidade: number;
  autoeficacia: number;
  networking: number;
  necessidade_realizacao: number;
  fase: FaseAtual;
  alertas: string[];
}

export interface EventoRodada {
  rodada: number;
  codigo: string;
  titulo: string;
  narrativa: string;
}

export interface LinhaRanking {
  posicao: number;
  empresa_id: number;
  empresa: string;
  aluno: string | null;
  patrimonio: number;
  caixa: number;
  divida: number;
  lucro_acumulado: number;
  participacao_mercado: number;
  preco: number | null;
  fase: FaseAtual;
}

export interface PainelAluno {
  empresa: Empresa;
  turma: Turma;
  decisao_atual: Decisao | null;
  ultima_decisao: Decisao | null;
  resultados: Resultado[];
  eventos: EventoRodada[];
  mercado: { empresa: string; propria: boolean; preco: number; participacao_mercado: number }[];
  posicao_ranking: number | null;
  total_empresas: number;
}

export interface DetalheTurma {
  turma: Turma;
  empresas: Empresa[];
  ranking: LinhaRanking[];
  eventos: EventoRodada[];
  mercado: { rodada: number; preco_medio: number; unidades: number; receita: number; lucro: number }[];
}

export interface OpcaoEvento {
  codigo: string;
  titulo: string;
  narrativa: string;
}
