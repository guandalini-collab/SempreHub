import React from "react";
import { reais } from "../formatos";
export interface ServicoMidia {
 id:string;nome:string;preco_unitario:number;unidade:string;cobranca:"POR_CAMPANHA"|"POR_UNIDADE_MIDIA";
 escopo:string;fonte:{url:string;titulo:string;data_consulta:string;trecho:string};referencia_tipo:string;
}
export interface Cotacao {midia_id:string;valor:number;fonte_url:string}
export interface Alocacao {id:string;quantidade:number}
export interface MidiaComServicos {id:string;preco_unitario:number;servicos_obrigatorios?:ServicoMidia[]}
function servicosSelecionados(selecao:Alocacao[],catalogo:MidiaComServicos[]){
 const temJingle=selecao.some(m=>m.id==="jingle");
 const itens=new Map<string,{servico:ServicoMidia;quantidade:number}>();
 for(const m of selecao){
  if(temJingle&&["radio-spot","radio-streaming"].includes(m.id))continue;
  for(const servico of catalogo.find(c=>c.id===m.id)?.servicos_obrigatorios??[]){
   itens.set(servico.id,{servico,quantidade:servico.cobranca==="POR_UNIDADE_MIDIA"?m.quantidade:1});
  }
 }
 return [...itens.values()];
}
export function contratarServicos(selecao:Alocacao[],catalogo:MidiaComServicos[]):Alocacao[]{
 return servicosSelecionados(selecao,catalogo).map(({servico,quantidade})=>({id:servico.id,quantidade}));
}
export function custosCampanha(selecao:Alocacao[],catalogo:MidiaComServicos[],cotacoes:Cotacao[]=[]){
 const base=selecao.reduce((s,m)=>s+(catalogo.find(c=>c.id===m.id)?.preco_unitario??0)*m.quantidade,0);
 const servicos=servicosSelecionados(selecao,catalogo).reduce((s,m)=>s+m.servico.preco_unitario*m.quantidade,0)+cotacoes.filter(c=>selecao.some(m=>m.id===c.midia_id)).reduce((s,c)=>s+c.valor,0);
 return {veiculacao:Math.round(base*100)/100,servicos:Math.round(servicos*100)/100,total:Math.round((base+servicos)*100)/100};
}
export function TabelaServicos({servicos,quantidade=1}:{servicos:ServicoMidia[];quantidade?:number}){
 if(!servicos.length)return <p className="mt-2 text-xs text-slate-600">Consulte o escopo do pacote e os custos sob consulta. Ausência de taxa precificada não significa ausência de despesas no mercado real.</p>;
 return <div className="mt-3 rounded-xl border border-cyan-200 bg-cyan-50 p-3"><h5 className="font-bold text-slate-800">Serviços obrigatórios na contratação</h5><p className="mb-2 text-xs text-slate-600">Ao selecionar a mídia, estes serviços também entram no orçamento.</p>{servicos.map(s=><article key={s.id} className="border-t border-cyan-200 py-2"><p className="text-sm font-semibold">{s.nome} · <span className="text-emerald-800">{reais(s.preco_unitario*(s.cobranca==="POR_UNIDADE_MIDIA"?quantidade:1))}</span></p><p className="text-xs text-slate-600">{s.cobranca==="POR_CAMPANHA"?"Uma produção por formato, produto e mês; repetir inserções não repete esta taxa.":`${quantidade} × ${reais(s.preco_unitario)} por unidade de mídia.`} {s.escopo}</p><a className="mt-1 inline-block text-xs font-semibold text-blue-700 underline" href={s.fonte.url} target="_blank" rel="noreferrer">Fonte de preço: {s.fonte.titulo} · consulta {s.fonte.data_consulta}</a><p className="text-xs text-slate-500">{s.referencia_tipo}</p></article>)}</div>;
}
