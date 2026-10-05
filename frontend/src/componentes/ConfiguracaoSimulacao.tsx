import React from "react";

import type { ConfiguracaoJogo, ConfiguracaoMotor } from "../tiposSimulacao";
import { Campo, EntradaNumero, estiloEntrada } from "./ui";

type CampoConfiguracao = {
  campo: keyof ConfiguracaoMotor;
  rotulo: string;
  ajuda: string;
  tipo: "moeda" | "percentual" | "inteiro";
  minimo?: number;
};

const CAMPOS_TRADICIONAL: CampoConfiguracao[] = [
  { campo: "capacidade_maquina", rotulo: "Capacidade de uma máquina", ajuda: "Unidades que uma máquina em boas condições pode produzir por mês.", tipo: "inteiro", minimo: 1 },
  { campo: "preco_maquina", rotulo: "Preço de uma máquina", ajuda: "Investimento disponível às empresas durante o jogo.", tipo: "moeda" },
  { campo: "vida_util_maquina", rotulo: "Vida útil da máquina", ajuda: "Meses usados para calcular a depreciação.", tipo: "inteiro", minimo: 1 },
  { campo: "custo_armazenagem", rotulo: "Armazenagem mensal", ajuda: "Percentual sobre o valor do estoque mantido.", tipo: "percentual" },
  { campo: "frete_rapido", rotulo: "Frete rápido por unidade", ajuda: "Custo de entrega por unidade vendida.", tipo: "moeda" },
  { campo: "frete_padrao", rotulo: "Frete padrão por unidade", ajuda: "Custo de entrega por unidade vendida.", tipo: "moeda" },
  { campo: "frete_economico", rotulo: "Frete econômico por unidade", ajuda: "Custo de entrega por unidade vendida.", tipo: "moeda" },
];

const CAMPOS_STARTUP: CampoConfiguracao[] = [
  { campo: "custo_nuvem_cliente", rotulo: "Nuvem por cliente atendido", ajuda: "Custo mensal da infraestrutura por cliente.", tipo: "moeda" },
  { campo: "churn_base", rotulo: "Cancelamento mensal de referência", ajuda: "Percentual inicial de clientes que deixam o serviço; a satisfação influencia o resultado.", tipo: "percentual" },
  { campo: "aliquota_servico", rotulo: "Tributação didática do serviço", ajuda: "Percentual usado na simulação; não representa enquadramento fiscal real.", tipo: "percentual" },
];

const PESOS: CampoConfiguracao[] = [
  { campo: "peso_lucro", rotulo: "Peso do lucro", ajuda: "Resultado econômico acumulado.", tipo: "percentual" },
  { campo: "peso_patrimonio", rotulo: "Peso do patrimônio", ajuda: "Ativos menos obrigações; capital dos investidores não vira lucro.", tipo: "percentual" },
  { campo: "peso_satisfacao", rotulo: "Peso da satisfação", ajuda: "Qualidade da experiência dos clientes.", tipo: "percentual" },
  { campo: "peso_participacao", rotulo: "Peso da participação nas decisões", ajuda: "Evidências de entrega e confirmação das decisões da equipe.", tipo: "percentual" },
];

export default function ConfiguracaoSimulacao({
  valores,
  aoMudar,
  bloqueado = false,
}: {
  valores: ConfiguracaoJogo;
  aoMudar: (valores: ConfiguracaoJogo) => void;
  bloqueado?: boolean;
}) {
  const config = valores.configuracao_simulacao;
  const somaPesos = config.peso_lucro + config.peso_patrimonio + config.peso_satisfacao + config.peso_participacao;
  return (
    <fieldset disabled={bloqueado} className="space-y-4 rounded-lg border border-slate-200 p-4">
      <legend className="px-1 text-sm font-semibold text-marinho">Modelo da simulação</legend>
      <div className="grid gap-4 sm:grid-cols-2">
        <Campo rotulo="Tipo de empresa" ajuda="O modelo define as decisões operacionais e os demonstrativos financeiros.">
          <select className={estiloEntrada} value={valores.modo_jogo} onChange={(e) => aoMudar({ ...valores, modo_jogo: e.target.value as ConfiguracaoJogo["modo_jogo"] })}>
            <option value="TRADICIONAL">Empresa tradicional · produção e estoque</option>
            <option value="STARTUP">Startup · clientes e serviço digital</option>
            <option value="LEGADO">Modelo básico · compatibilidade com turmas anteriores</option>
          </select>
        </Campo>
        {valores.modo_jogo !== "LEGADO" && <Campo rotulo="Situação inicial" ajuda="A história começa no mês 1 e os resultados das rodadas passam a ser registrados a partir daí.">
          <select className={estiloEntrada} value={valores.cenario} onChange={(e) => aoMudar({ ...valores, cenario: e.target.value as ConfiguracaoJogo["cenario"] })}>
            <option value="ZERO">Começar do zero</option>
            <option value="CRISE">Recuperar uma empresa em crise</option>
          </select>
        </Campo>}
      </div>
      {bloqueado && <p className="text-xs text-slate-500">Tipo, cenário e regras operacionais ficam definidos quando a primeira empresa entra na turma.</p>}
      {valores.modo_jogo === "TRADICIONAL" && <p className="text-xs text-slate-600">Os alunos planejam matéria-prima, produção, máquinas, entregas e prazos. O estoque e as obrigações passam para a rodada seguinte.</p>}
      {valores.modo_jogo === "STARTUP" && <p className="text-xs text-slate-600">Os alunos administram aquisição e retenção de clientes, capacidade da nuvem e investimento externo, com acompanhamento de CAC, LTV e participação dos fundadores.</p>}
      {valores.modo_jogo !== "LEGADO" && <>
        {valores.cenario === "CRISE" && <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">O cenário de crise começa com menos caixa, dívida e contas a receber e a pagar. As primeiras decisões precisam considerar os vencimentos e recuperar a operação.</p>}
        <details>
          <summary className="cursor-pointer text-sm font-semibold text-marinho">Ajustar operação e avaliação</summary>
          <div className="mt-4 space-y-5">
            <GrupoCampos titulo={valores.modo_jogo === "STARTUP" ? "Serviço digital" : "Produção e entregas"} campos={valores.modo_jogo === "STARTUP" ? CAMPOS_STARTUP : CAMPOS_TRADICIONAL} valores={config} aoMudar={(proxima) => aoMudar({ ...valores, configuracao_simulacao: proxima })} />
            <Campo rotulo="Concorrentes virtuais" ajuda="Empresas simuladas também disputam o mercado. A quantidade de concorrentes não aumenta a demanda total.">
              <EntradaNumero inteiro valor={config.concorrentes_virtuais} aoMudar={(valor) => aoMudar({ ...valores, configuracao_simulacao: { ...config, concorrentes_virtuais: valor } })} />
            </Campo>
            <GrupoCampos titulo="Pesos da avaliação" campos={PESOS} valores={config} aoMudar={(proxima) => aoMudar({ ...valores, configuracao_simulacao: proxima })} />
            <p className={`text-xs font-semibold ${Math.abs(somaPesos - 1) < 0.000001 ? "text-emerald-700" : "text-red-700"}`}>Os pesos devem somar 100%. Soma atual: {(somaPesos * 100).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%.</p>
          </div>
        </details>
      </>}
    </fieldset>
  );
}

function GrupoCampos({ titulo, campos, valores, aoMudar }: { titulo: string; campos: CampoConfiguracao[]; valores: ConfiguracaoMotor; aoMudar: (valores: ConfiguracaoMotor) => void }) {
  return <fieldset>
    <legend className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-600">{titulo}</legend>
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {campos.map((campo) => <Campo key={campo.campo} rotulo={campo.rotulo} ajuda={campo.ajuda}>
        <EntradaNumero valor={campo.tipo === "percentual" ? Math.round(valores[campo.campo] * 1000000) / 10000 : valores[campo.campo]} moeda={campo.tipo === "moeda"} inteiro={campo.tipo === "inteiro"} sufixo={campo.tipo === "percentual" ? "%" : undefined} minimo={campo.minimo ?? 0} aoMudar={(valor) => aoMudar({ ...valores, [campo.campo]: campo.tipo === "percentual" ? valor / 100 : valor })} />
      </Campo>)}
    </div>
  </fieldset>;
}
