import React from "react";

import { Campo, EntradaNumero } from "../../componentes/ui";
import type { Parametros } from "../../tipos";

export const PARAMETROS_PADRAO: Parametros = {
  total_rodadas: 12,
  caixa_inicial: 20000,
  preco_referencia: 100,
  custo_unitario: 40,
  demanda_base_por_empresa: 220,
  crescimento_mercado_mensal: 0.01,
  produtividade_por_pessoa: 120,
  custos_fixos_mensais: 1500,
  salario_base: 2000,
  taxa_juros_mensal: 0.025,
  taxa_cheque_especial: 0.08,
  limite_credito: 50000,
  probabilidade_evento: 0.35,
  teto_mei_anual: 81000,
  das_mei_mensal: 81,
  aliquota_icms: 0.17,
};

type Definicao = {
  campo: keyof Parametros;
  rotulo: string;
  ajuda: string;
  percentual?: boolean;
  passo?: number;
};

const GRUPOS: { titulo: string; campos: Definicao[] }[] = [
  {
    titulo: "Jogo",
    campos: [
      { campo: "total_rodadas", rotulo: "Total de rodadas (meses)", ajuda: "Cada rodada representa um mês." },
      { campo: "caixa_inicial", rotulo: "Caixa inicial (R$)", ajuda: "Capital com que cada empresa começa.", passo: 1000 },
      { campo: "probabilidade_evento", rotulo: "Chance de evento ao sortear (%)", ajuda: "Usada quando você escolhe “sortear”.", percentual: true },
    ],
  },
  {
    titulo: "Mercado",
    campos: [
      { campo: "preco_referencia", rotulo: "Preço de referência (R$)", ajuda: "Preço “justo” percebido pelos clientes.", passo: 1 },
      { campo: "custo_unitario", rotulo: "Custo da mercadoria (R$/un.)", ajuda: "CMV por unidade vendida.", passo: 1 },
      { campo: "demanda_base_por_empresa", rotulo: "Demanda base por empresa (un./mês)", ajuda: "O mercado total cresce com o número de empresas.", passo: 10 },
      { campo: "crescimento_mercado_mensal", rotulo: "Crescimento do mercado (% ao mês)", ajuda: "Crescimento vegetativo da demanda.", percentual: true },
      { campo: "produtividade_por_pessoa", rotulo: "Produtividade (un./pessoa/mês)", ajuda: "O dono também produz.", passo: 10 },
    ],
  },
  {
    titulo: "Custos e crédito",
    campos: [
      { campo: "custos_fixos_mensais", rotulo: "Custos fixos (R$/mês)", ajuda: "Aluguel, energia, contador etc.", passo: 100 },
      { campo: "salario_base", rotulo: "Salário-base (R$)", ajuda: "Sem encargos.", passo: 100 },
      { campo: "taxa_juros_mensal", rotulo: "Juros do empréstimo (% ao mês)", ajuda: "Muda com eventos de Selic.", percentual: true },
      { campo: "taxa_cheque_especial", rotulo: "Juros do cheque especial (% ao mês)", ajuda: "Cobrados sobre caixa negativo.", percentual: true },
      { campo: "limite_credito", rotulo: "Limite de crédito (R$)", ajuda: "Dívida máxima por empresa.", passo: 1000 },
    ],
  },
  {
    titulo: "Tributos",
    campos: [
      { campo: "teto_mei_anual", rotulo: "Teto anual do MEI (R$)", ajuda: "Confira o valor vigente na legislação.", passo: 1000 },
      { campo: "das_mei_mensal", rotulo: "DAS do MEI (R$/mês)", ajuda: "Confira o valor vigente para comércio.", passo: 1 },
      { campo: "aliquota_icms", rotulo: "ICMS no Lucro Presumido (%)", ajuda: "Aplicado sobre o valor agregado.", percentual: true },
    ],
  },
];

export function EditorParametros({
  valores,
  aoMudar,
  somenteRodadas = false,
}: {
  valores: Parametros;
  aoMudar: (valores: Parametros) => void;
  somenteRodadas?: boolean;
}) {
  return (
    <div className="space-y-5">
      {GRUPOS.map((grupo) => (
        <fieldset key={grupo.titulo}>
          <legend className="mb-3 border-b border-slate-200 pb-1 text-sm font-semibold text-marinho">{grupo.titulo}</legend>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {grupo.campos.map((def) => {
              const bloqueado = somenteRodadas && def.campo !== "total_rodadas";
              const valor = valores[def.campo];
              return (
                <Campo key={def.campo} rotulo={def.rotulo} ajuda={def.ajuda}>
                  <EntradaNumero
                    disabled={bloqueado}
                    valor={def.percentual ? Math.round(valor * 10000) / 100 : valor}
                    passo={def.percentual ? 0.1 : def.passo ?? 1}
                    aoMudar={(v) => aoMudar({ ...valores, [def.campo]: def.percentual ? v / 100 : v })}
                  />
                </Campo>
              );
            })}
          </div>
        </fieldset>
      ))}
      {somenteRodadas && (
        <p className="text-xs text-slate-500">
          Depois da primeira rodada, apenas o total de rodadas pode ser alterado, para não distorcer a competição.
        </p>
      )}
    </div>
  );
}

export function useParametros(inicial?: Parametros) {
  return React.useState<Parametros>(inicial ?? PARAMETROS_PADRAO);
}
