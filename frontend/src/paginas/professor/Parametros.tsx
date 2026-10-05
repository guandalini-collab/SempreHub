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
  das_mei_mensal: 82.05,
  aliquota_icms: 0.17,
};

type Definicao = {
  campo: keyof Parametros;
  rotulo: string;
  ajuda: string;
  tipo: "moeda" | "percentual" | "inteiro" | "decimal";
};

const GRUPOS: { titulo: string; campos: Definicao[] }[] = [
  {
    titulo: "Jogo",
    campos: [
      { campo: "total_rodadas", rotulo: "Total de rodadas (meses)", ajuda: "Cada rodada representa um mês.", tipo: "inteiro" },
      { campo: "caixa_inicial", rotulo: "Caixa inicial", ajuda: "Capital com que cada empresa começa.", tipo: "moeda" },
      { campo: "probabilidade_evento", rotulo: "Chance de evento ao sortear", ajuda: "Usada quando você escolhe “sortear”.", tipo: "percentual" },
    ],
  },
  {
    titulo: "Mercado",
    campos: [
      { campo: "preco_referencia", rotulo: "Preço de referência", ajuda: "Preço “justo” percebido pelos clientes.", tipo: "moeda" },
      { campo: "custo_unitario", rotulo: "Custo da mercadoria (por unidade)", ajuda: "CMV por unidade vendida.", tipo: "moeda" },
      { campo: "demanda_base_por_empresa", rotulo: "Demanda base por empresa (un./mês)", ajuda: "O mercado total cresce com o número de empresas.", tipo: "decimal" },
      { campo: "crescimento_mercado_mensal", rotulo: "Crescimento do mercado (ao mês)", ajuda: "Crescimento vegetativo da demanda.", tipo: "percentual" },
      { campo: "produtividade_por_pessoa", rotulo: "Produtividade (un./pessoa/mês)", ajuda: "O dono também produz.", tipo: "decimal" },
    ],
  },
  {
    titulo: "Custos e crédito",
    campos: [
      { campo: "custos_fixos_mensais", rotulo: "Custos fixos (por mês)", ajuda: "Aluguel, energia, contador etc.", tipo: "moeda" },
      { campo: "salario_base", rotulo: "Salário-base", ajuda: "Sem encargos.", tipo: "moeda" },
      { campo: "taxa_juros_mensal", rotulo: "Juros do empréstimo (ao mês)", ajuda: "Muda com eventos de Selic.", tipo: "percentual" },
      { campo: "taxa_cheque_especial", rotulo: "Juros do cheque especial (ao mês)", ajuda: "Cobrados sobre caixa negativo.", tipo: "percentual" },
      { campo: "limite_credito", rotulo: "Limite de crédito", ajuda: "Dívida máxima por empresa.", tipo: "moeda" },
    ],
  },
  {
    titulo: "Tributos",
    campos: [
      { campo: "teto_mei_anual", rotulo: "Teto anual do MEI", ajuda: "Confira o valor vigente na legislação.", tipo: "moeda" },
      { campo: "das_mei_mensal", rotulo: "DAS do MEI (por mês)", ajuda: "Confira o valor vigente para comércio.", tipo: "moeda" },
      { campo: "aliquota_icms", rotulo: "ICMS no Lucro Presumido", ajuda: "Aplicado sobre o valor agregado.", tipo: "percentual" },
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
                    minimo={def.campo === "crescimento_mercado_mensal" ? -20 : 0}
                    valor={def.tipo === "percentual" ? Math.round(valor * 1000000) / 10000 : valor}
                    moeda={def.tipo === "moeda"}
                    inteiro={def.tipo === "inteiro"}
                    sufixo={def.tipo === "percentual" ? "%" : undefined}
                    casas={def.tipo === "percentual" ? 2 : undefined}
                    aoMudar={(v) => aoMudar({ ...valores, [def.campo]: def.tipo === "percentual" ? v / 100 : v })}
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
