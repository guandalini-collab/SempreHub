import React from "react";
import catalogo from "../indicadores.json";
import type { Resultado } from "../tipos";
import { Cartao } from "./ui";
import { reais, percentual } from "../formatos";

export const AREAS_INDICADORES = [{id:"liquidez",titulo:"Liquidez"},{id:"marketing",titulo:"Marketing"},{id:"financas",titulo:"Finanças"},{id:"rh",titulo:"Recursos humanos"},{id:"producao",titulo:"Produção"},{id:"logistica",titulo:"Logística"}];
export default function IndicadoresDepartamentais({area,resultado}:{area:string;resultado?:Resultado}) {
 const d=resultado?.dre, detalhe=resultado?.detalhes_simulacao, op=detalhe?.operacao;
 const numero=(k:string)=>typeof op?.[k]==="number"?op[k] as number:null;
 const razao=(a:number|null|undefined,b:number|null|undefined)=>a!=null&&b!=null&&b>0?a/b:null;
 const valores:Record<string,{valor:number|null;tipo?:string;nota?:string;status?:string}>={};
 if(resultado&&d){
  valores['Margem Bruta']={valor:razao(d.receita-d.impostos-d.cmv,d.receita-d.impostos),tipo:'percentual',nota:'Base: receita líquida de tributos sobre vendas.'};
  valores['Margem Líquida']={valor:razao(d.lucro_liquido,d.receita),tipo:'percentual'};
  valores['CAC']={valor:numero('cac'),tipo:'moeda',nota:'Estimativa do modelo de aquisição de clientes.'};
  valores['LTV']={valor:numero('ltv'),tipo:'moeda',nota:'Estimativa do modelo de assinatura e cancelamento.'};
  valores['Relação LTV / CAC']={valor:razao(numero('ltv'),numero('cac')),tipo:'razao'};
  valores['Receita por Funcionário']={valor:razao(d.receita,resultado.funcionarios),tipo:'moeda'};
  valores['eNPS']={valor:numero('enps'),tipo:'pontos'};
  valores['OEE']={valor:numero('oee'),tipo:'percentual',nota:'Eficiência esperada do modelo; refugo realizado é arredondado para unidades inteiras.'};
  valores['OTIF']={valor:numero('otif'),tipo:'percentual',nota:op?.convencao_pedidos?'Modelo didático: cada unidade demandada representa um pedido; falhas são contadas uma única vez.':undefined};
  valores['Taxa de Refugo']={valor:razao(numero('refugo'),numero('producao_real')),tipo:'percentual'};
  valores['Capacidade Instalada Utilizada']={valor:razao(numero('producao_real'),numero('capacidade_nominal_periodo')??numero('capacidade_maquinas')),tipo:'percentual',nota:'Base: capacidade nominal do período, incluindo horas extras quando utilizadas.'};
  const adm=numero('admissoes'),dem=numero('demissoes'),sai=numero('turnover');
  valores['Turnover']={valor:adm!=null&&dem!=null&&sai!=null?razao((adm+dem+sai)/2,resultado.funcionarios):null,tipo:'percentual'};
  valores['Custo Logístico / Faturamento']={valor:detalhe?.modo==='TRADICIONAL'?razao((d.frete??0)+(d.armazenagem??0),d.receita):null,tipo:'percentual',nota:'Custos logísticos registrados: frete e armazenagem.'};
  for(const [nome,chave] of [['Liquidez Corrente','liquidez_corrente'],['Liquidez Seca','liquidez_seca'],['Liquidez Imediata','liquidez_imediata'],['Liquidez Geral','liquidez_geral']]) valores[nome]={valor:numero(chave),tipo:'razao'};
  valores['EBITDA (Lajida)']={valor:numero('ebitda'),tipo:'moeda'};
  valores['Prazo Médio de Recebimento (PMR)']={valor:numero('pmr'),nota:'Base: recebíveis originados na rodada e faturamento mensal; ciclo de 30 dias.'};
  valores['Prazo Médio de Pagamento (PMP)']={valor:numero('pmp'),nota:'Base: fornecedores originados na rodada e compras de insumos do mês; ciclo de 30 dias.'};
  valores['Ponto de Equilíbrio']={valor:numero('ponto_equilibrio'),tipo:'moeda',status:typeof op?.ponto_equilibrio_status==='string'?op.ponto_equilibrio_status:undefined};
  if(detalhe?.modo==='TRADICIONAL')valores['LTV']={valor:null,status:'Dados indisponíveis'};
 }
 const formato=(v:number,t?:string)=>t==='moeda'?reais(v):t==='percentual'?percentual(v,2):t==='razao'?v.toLocaleString('pt-BR',{maximumFractionDigits:2})+':1':v.toLocaleString('pt-BR',{maximumFractionDigits:2})+(t==='pontos'?' pontos':'');
 return <Cartao titulo={`${AREAS_INDICADORES.find(a=>a.id===area)?.titulo} · ${resultado?`rodada ${resultado.rodada}`:'aguardando resultados'}`}>
  <p className="mb-4 text-sm text-slate-600">Resultados da simulação. Consulte o capítulo de indicadores no manual do aluno e discuta com sua equipe antes da próxima decisão.</p>
  <div className="grid gap-4 sm:grid-cols-2">{catalogo.filter(i=>i.area===area).map(i=>{const item=valores[i.nome],v=item?.valor;const naoAplica=resultado&&['OEE','OTIF','eNPS'].includes(i.nome)&&op&&i.nome.toLowerCase() in op&&v==null;return <article key={i.id} className="rounded-xl border border-blue-100 bg-slate-50 p-4"><h3 className="font-semibold">{i.nome}</h3><p className="mt-2 text-xl font-bold text-marinho">{v!=null&&Number.isFinite(v)?formato(v,item.tipo):naoAplica?'Não se aplica':item?.status??(resultado?'Dados indisponíveis':'—')}</p>{v==null&&!naoAplica&&<p className="mt-2 text-xs text-slate-500">{resultado?'Dados necessários não registrados nesta rodada.':'Disponível após o fechamento da rodada.'}</p>}{item?.nota&&v!=null&&<p className="mt-2 text-xs text-slate-500">{item.nota}</p>}</article>})}</div>
  {area==='producao'&&numero('oee')!=null&&<p className="mt-4 text-sm">Disponibilidade: {percentual(numero('disponibilidade')!,2)} · Performance: {percentual(numero('performance')!,2)} · Qualidade: {percentual(numero('qualidade_oee')!,2)}</p>}
  {area==='rh'&&numero('enps')!=null&&<p className="mt-4 text-sm">Pesquisa simulada: {numero('enps_promotores')} promotores · {numero('enps_neutros')} neutros · {numero('enps_detratores')} detratores.</p>}
 </Cartao>;
}
