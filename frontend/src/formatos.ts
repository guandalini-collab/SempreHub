import type { ClasseDornelas, FaseAtual, RegimeTributario, TipoEntradaGem } from "./tipos";

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const numero = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1, minimumFractionDigits: 1 });

export const reais = (valor: number) => moeda.format(valor);
export const inteiro = (valor: number) => numero.format(valor);
export const umDecimal = (valor: number) => decimal.format(valor);
export const percentual = (valor: number, casas = 1) =>
  `${(valor * 100).toLocaleString("pt-BR", { maximumFractionDigits: casas, minimumFractionDigits: casas })}%`;

export const NOME_REGIME: Record<RegimeTributario, string> = {
  MEI: "MEI",
  SIMPLES_NACIONAL: "Simples Nacional",
  LUCRO_PRESUMIDO: "Lucro Presumido",
};

export const NOME_FASE: Record<FaseAtual, string> = {
  IDEACAO: "Ideação",
  PLANEJAMENTO: "Planejamento",
  CAPTACAO: "Captação",
  OPERACAO_ESTAVEL: "Operação estável",
  SOBREVIVENCIA: "Sobrevivência",
};

export const NOME_GEM: Record<TipoEntradaGem, string> = {
  OPORTUNIDADE: "Por oportunidade",
  NECESSIDADE: "Por necessidade",
};

export const NOME_DORNELAS: Record<ClasseDornelas, string> = {
  SERIAL: "Empreendedor serial",
  FRANQUIA: "Franqueado",
  CORPORATIVO: "Corporativo",
  SOCIAL: "Social",
};

export const DESCRICAO_DORNELAS: Record<ClasseDornelas, string> = {
  SERIAL: "Já empreendeu antes: começa com mais networking e autoconfiança.",
  FRANQUIA: "Começa com marca conhecida, mas paga 5% da receita em royalties.",
  CORPORATIVO: "Traz processos de grandes empresas: começa com qualidade maior.",
  SOCIAL: "Movido por impacto: começa com rede de contatos comunitária.",
};

export const DESCRICAO_GEM: Record<TipoEntradaGem, string> = {
  OPORTUNIDADE: "Identificou uma oportunidade de mercado. Começa com autoeficácia 60.",
  NECESSIDADE: "Empreende por falta de alternativa de renda. Começa com autoeficácia 45.",
};

export const DESCRICAO_REGIME: Record<RegimeTributario, string> = {
  MEI: "DAS fixo mensal, teto de faturamento anual e no máximo 1 empregado.",
  SIMPLES_NACIONAL: "Alíquota única que cresce com o faturamento dos últimos 12 meses (Anexo I).",
  LUCRO_PRESUMIDO: "Tributos federais de 5,93% da receita + ICMS sobre o valor agregado; encargos da folha maiores.",
};

export function corFase(fase: FaseAtual): string {
  switch (fase) {
    case "SOBREVIVENCIA":
      return "bg-red-100 text-red-800 ring-red-300";
    case "OPERACAO_ESTAVEL":
      return "bg-emerald-100 text-emerald-800 ring-emerald-300";
    case "CAPTACAO":
      return "bg-amber-100 text-amber-800 ring-amber-300";
    default:
      return "bg-slate-100 text-slate-700 ring-slate-300";
  }
}
