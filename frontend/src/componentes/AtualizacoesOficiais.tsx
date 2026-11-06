import {useEffect,useState} from 'react';
import {api} from '../api';
import {Cartao} from './ui';

type Impacto={departamento:string;efeito:string;como_interpretar:string};
type Item={titulo:string;tema:string;resumo:string;instituicao:string;url:string;publicado_em:string;referencia:string;vigencia_inicio:string|null;vigencia_fim:string|null;condicoes:string|null;competencia?:string|null;setores_afetados?:string[];impactos?:Impacto[]};
type Boletim={habilitado:boolean;estado:string;erro:string|null;consultado_em:string|null;consulta_vencida:boolean;itens:Item[];escopo:string;setor?:string|null;setor_sem_item_especifico?:boolean};
const dividir=(texto:string)=>{const partes:string[]=[];let resto=texto;while(resto.length>400){const ponto=resto.lastIndexOf(' ',400);const n=ponto>200?ponto:400;partes.push(resto.slice(0,n));resto=resto.slice(n).trimStart();}if(resto)partes.push(resto);return partes;};
const data=(s:string)=>new Date(s.length===10?s+'T12:00:00':s).toLocaleString('pt-BR',s.length===10?{day:'2-digit',month:'2-digit',year:'numeric'}:{timeZone:'America/Sao_Paulo'});
export default function AtualizacoesOficiais({empresaId,turmaId}:{empresaId?:number;turmaId?:number}){
 const [dados,setDados]=useState<Boletim|null>(null),[erro,setErro]=useState(''),[pagina,setPagina]=useState(0);
 const url=turmaId?`/api/professor/turmas/${turmaId}/atualizacoes-oficiais`:`/api/aluno/empresas/${empresaId}/atualizacoes-oficiais`;
 useEffect(()=>{let ativo=true;const ler=()=>api.get<Boletim>(url).then(d=>{if(ativo){setDados(d);setErro('');}}).catch(e=>{if(ativo)setErro(e.message);});ler();const timer=setInterval(ler,60000);return()=>{ativo=false;clearInterval(timer);};},[url]);
 const paginas=(dados?.itens??[]).flatMap(i=>dividir(i.resumo+(i.condicoes?' Condições de aplicação: '+i.condicoes:'')).map(resumo=>({...i,resumo,condicoes:null})));
 const paginaAtual=Math.min(pagina,Math.max(0,paginas.length-1)),item=paginas[paginaAtual];
 const setores=item?.setores_afetados??[], impactos=item?.impactos??[];
 return <Cartao titulo="Atualizações oficiais">
  {erro&&<p role="alert">{erro}</p>}
  {!dados&&!erro&&<p>Consultando o serviço…</p>}
  {dados&&<>
   <p className="mb-2 text-xs text-slate-500">{dados.consultado_em?`Última consulta: ${data(dados.consultado_em)} · Brasília`:'Ainda não há uma consulta confirmada.'} · Consulta automática a cada 6 horas.</p>
   {(!dados.habilitado||dados.consulta_vencida||dados.erro)&&<p role="status" className="mb-2 rounded border-l-4 border-amber-500 bg-amber-50 p-2 text-sm">{!dados.habilitado?'Integração indisponível. A configuração da API precisa ser verificada.':dados.erro||'Nova consulta automática pendente. A edição anterior, quando existente, permanece identificada pela data.'}</p>}
   {dados.setor_sem_item_especifico&&<p className="mb-3 rounded border-l-4 border-cyan-500 bg-cyan-50 p-3 text-sm">Ainda não houve uma publicação oficial exclusiva para <strong>{dados.setor}</strong> nesta consulta. O boletim nacional mais recente permanece visível para que a equipe não decida sem dados.</p>}
   {!item&&<p className="rounded border-l-4 border-cyan-500 bg-cyan-50 p-3 text-sm">A fonte oficial ainda não confirmou um novo item. A última edição validada é preservada; a equipe pode consultar as notícias setoriais e os indicadores da empresa.</p>}
   {item&&<article className="rounded-lg border border-slate-200 p-3"><p className="text-xs text-slate-500">{item.tema} · Referência: {item.referencia}</p><h3 className="my-2 font-bold">{item.titulo}</h3><p className="text-sm">{item.resumo}</p><p className="mt-2 text-xs">Publicação: {data(item.publicado_em)}{item.competencia&&` · Competência: ${item.competencia}`}{item.vigencia_inicio&&` · Início dos efeitos: ${data(item.vigencia_inicio)}`}{item.vigencia_fim&&` · Fim: ${data(item.vigencia_fim)}`}</p>{setores.length>0&&<p className="mt-2 text-xs text-slate-600">Setores afetados: {setores.join(' · ')}</p>}{item.condicoes&&<p className="mt-2 text-xs text-amber-900">Condições: {item.condicoes}</p>}{impactos.length>0&&<details className="mt-3 rounded bg-slate-50 p-3"><summary className="cursor-pointer text-sm font-semibold">Como isso pode afetar as decisões da empresa</summary><div className="mt-3 space-y-3">{impactos.map((impacto,n)=><section key={`${impacto.departamento}-${n}`} className="border-l-2 border-cyan-500 pl-3 text-sm"><strong>{impacto.departamento}</strong><p>{impacto.efeito}</p><p className="mt-1 text-slate-600">Antes de decidir: {impacto.como_interpretar}</p></section>)}</div></details>}<a className="mt-2 inline-block text-sm underline" href={item.url} target="_blank" rel="noopener noreferrer">{item.instituicao} · consultar fonte oficial ↗</a></article>}
   {paginas.length>1&&<nav className="mt-3 flex justify-between text-sm" aria-label="Atualizações oficiais"><button disabled={paginaAtual===0} onClick={()=>setPagina(paginaAtual-1)}>← Anterior</button><span>{paginaAtual+1}/{paginas.length}</span><button disabled={paginaAtual+1>=paginas.length} onClick={()=>setPagina(paginaAtual+1)}>Próxima →</button></nav>}
   <p className="mt-2 text-xs text-slate-500">{dados.escopo}</p>
  </>}
 </Cartao>;
}
