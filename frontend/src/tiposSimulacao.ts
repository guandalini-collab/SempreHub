export type ModoJogo = "LEGADO" | "TRADICIONAL" | "STARTUP";
export type CenarioJogo = "ZERO" | "CRISE";
export type ModalLogistica = "RAPIDO" | "PADRAO" | "ECONOMICO";
export type Posicionamento = "CUSTO" | "DIFERENCIACAO";
export type CanalVenda = "DIRETO" | "DISTRIBUIDOR" | "DIGITAL";

export interface ConfiguracaoMotor {
  capacidade_maquina: number;
  preco_maquina: number;
  vida_util_maquina: number;
  custo_armazenagem: number;
  frete_rapido: number;
  frete_padrao: number;
  frete_economico: number;
  custo_nuvem_cliente: number;
  churn_base: number;
  aliquota_servico: number;
  concorrentes_virtuais: number;
  nivel_concorrencia: "BAIXA" | "MEDIA" | "ALTA";
  estrutura_mercado: "MONOPOLIO" | "OLIGOPOLIO" | "MONOPOLISTICA" | "PERFEITA" | "FRAGMENTADO";
  forca_concorrentes: "FRACA" | "MEDIA" | "FORTE" | "MUITO_FORTE";
  peso_lucro: number;
  peso_patrimonio: number;
  peso_satisfacao: number;
  peso_participacao: number;
}

export interface ConfiguracaoJogo {
  modo_jogo: ModoJogo;
  cenario: CenarioJogo;
  configuracao_simulacao: ConfiguracaoMotor;
}

export interface DecisaoSimulacao {
  producao: number;
  comprar_mp: number;
  comprar_maquinas: number;
  manutencao: number;
  modal: ModalLogistica;
  salario: number | null;
  beneficio: number;
  treinamento: number;
  vendas_prazo: number;
  prazo_recebimento: number;
  compras_prazo: number;
  prazo_pagamento: number;
  posicionamento: Posicionamento;
  canal: CanalVenda;
  marketing_digital: number;
  capacidade_nuvem: number;
  aporte: number;
  valuation: number;
}

export interface EstoqueSimulacao {
  quantidade: number;
  valor: number;
}

export interface MaquinaSimulacao {
  custo: number;
  valor_liquido: number;
  capacidade: number;
  condicao: number;
  ativacao: number;
  vida_util: number;
}

export interface TituloFinanceiro {
  origem: number;
  vencimento: number;
  valor: number;
}

export interface EstadoSimulacao {
  versao: number;
  estoque_mp: EstoqueSimulacao;
  estoque_pa: EstoqueSimulacao;
  estoque_obsoleto: EstoqueSimulacao;
  maquinas: MaquinaSimulacao[];
  receber: TituloFinanceiro[];
  pagar: TituloFinanceiro[];
  rh: { moral: number; qualificacao: number; rotatividade_acumulada: number };
  satisfacao: number;
  clientes: number;
  participacao_fundadores: number;
  capital_aportado: number;
  vencimento_divida?: number;
}

export interface FluxoCaixa {
  caixa_inicial: number;
  recebimentos: number;
  pagamentos: number;
  operacional: number;
  investimento: number;
  financiamento: number;
  variacao: number;
  caixa_final: number;
}

export interface BalancoSimulacao {
  caixa: number;
  receber: number;
  pagar: number;
  estoques: number;
  imobilizado: number;
  divida: number;
  patrimonio: number;
  capital_giro: number;
}

export interface DetalhesSimulacao {
  versao_motor: number;
  modo: ModoJogo;
  estado_inicial: EstadoSimulacao;
  estado_final: EstadoSimulacao;
  operacao: Record<string, number | string | null>;
  dfc: FluxoCaixa;
  balanco: BalancoSimulacao;
}

export interface PreviaSimulacao {
  estado: EstadoSimulacao;
  producao?: number;
  emprestimo?: number;
  amortizacao?: number;
  aviso?: string;
}

export const CONFIGURACAO_MOTOR_PADRAO: ConfiguracaoMotor = {
  capacidade_maquina: 240,
  preco_maquina: 12000,
  vida_util_maquina: 24,
  custo_armazenagem: 0.01,
  frete_rapido: 15,
  frete_padrao: 10,
  frete_economico: 5,
  custo_nuvem_cliente: 10,
  churn_base: 0.05,
  aliquota_servico: 0.06,
  concorrentes_virtuais: 0,
  nivel_concorrencia: "MEDIA",
  estrutura_mercado: "FRAGMENTADO",
  forca_concorrentes: "MEDIA",
  peso_lucro: 0.4,
  peso_patrimonio: 0.3,
  peso_satisfacao: 0.2,
  peso_participacao: 0.1,
};

export const DECISAO_SIMULACAO_PADRAO: DecisaoSimulacao = {
  producao: 0,
  comprar_mp: 0,
  comprar_maquinas: 0,
  manutencao: 0,
  modal: "PADRAO",
  salario: null,
  beneficio: 0,
  treinamento: 0,
  vendas_prazo: 0,
  prazo_recebimento: 1,
  compras_prazo: 0,
  prazo_pagamento: 1,
  posicionamento: "CUSTO",
  canal: "DIRETO",
  marketing_digital: 0,
  capacidade_nuvem: 300,
  aporte: 0,
  valuation: 100000,
};
