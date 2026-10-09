import React from "react";
import type { ConfiguracaoMotor } from "../tiposSimulacao";
import { Cartao } from "./ui";

const NOMES: Record<string, string> = { BAIXA: "Baixa", MEDIA: "Média", ALTA: "Alta", FRACA: "Fraca", FORTE: "Forte", MUITO_FORTE: "Muito forte", MONOPOLIO: "Monopólio", OLIGOPOLIO: "Oligopólio", MONOPOLISTICA: "Concorrência monopolística", PERFEITA: "Concorrência perfeita", FRAGMENTADO: "Fragmentado" };
export default function CompetitividadeMercado({ config, equipes }: { config: ConfiguracaoMotor; equipes: number }) {
  return <Cartao titulo="Competitividade do mercado">
    <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
      {[["Equipes disputando clientes", equipes], ["Concorrentes externos simulados", config.concorrentes_virtuais], ["Nível / força externa", `${NOMES[config.nivel_concorrencia]} / ${NOMES[config.forca_concorrentes]}`], ["Estrutura do mercado", NOMES[config.estrutura_mercado]]].map(([nome, valor]) => <div key={nome}><dt className="text-slate-500">{nome}</dt><dd className="mt-1 font-semibold text-marinho">{valor}</dd></div>)}
    </dl>
    <p className="mt-3 text-sm text-slate-600">Vocês disputam a mesma demanda com as outras equipes e os concorrentes externos. Preço, marca, qualidade do produto e capacidade de atendimento afetam as vendas. Produzir mais não garante vender mais; crescimento do mercado e eventos econômicos também afetam os resultados.</p>
    <p className="mt-2 text-xs text-slate-500">Nível, força e estrutura são parâmetros do cenário. Quando não há concorrentes externos, esses fatores não acrescentam pressão externa. As participações e preços realizados aparecem após o fechamento; decisões privadas das equipes não são divulgadas.</p>
  </Cartao>;
}
