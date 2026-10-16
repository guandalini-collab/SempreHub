import {useEffect,useRef,useState} from 'react';
import {api} from '../api';
import {Cartao,estiloEntrada} from './ui';
import type {Resultado} from '../tipos';

type Meta={alvo?:number;alerta?:number};
type Dado={valor:number|null;estado:string;unidade:string;meta?:Meta&{status:string;direcao:string}};
type Dados={bases:Record<string,number>;metas:Record<string,Meta>;direcoes:Record<string,Record<string,string>>;indicadores:Record<string,Record<string,Dado>>;atualizado_em:string|null};
const AREAS=[
 {id:'marketing',nome:'Marketing e vendas',campos:[['marketing','Investimento de aquisição da semana','R$'],['anuncios','Gasto com anúncios da semana','R$'],['novos_clientes','Novos clientes faturados',''],['pedidos','Pedidos faturados',''],['leads','Leads / visitantes',''],['cliques','Cliques',''],['cancelamentos','Clientes cancelados ou pausados distintos',''],['base_recorrentes','Clientes recorrentes no início',''],['promotores','NPS: respostas 9 e 10',''],['neutros','NPS: respostas 7 e 8',''],['detratores','NPS: respostas 0 a 6','']]},
 {id:'rh',nome:'Pessoas',campos:[['horas_ausencia','Horas de ausência','h'],['horas_contratadas','Horas contratadas totais','h'],['horas_extras_realizadas','Horas extras realizadas pela equipe','h'],['desligamentos','Desligamentos informados',''],['colaboradores_inicio','Colaboradores no início da semana','']]},
 {id:'producao',nome:'Produção',campos:[['ciclo_minutos','Tempo total dos ciclos medidos','min'],['ciclos_concluidos','Ciclos concluídos (unidade ou lote)','']]},
 {id:'logistica',nome:'Logística',campos:[['picking_minutos','Tempo médio de separação observado','min'],['custo_logistico','Custo logístico total informado','R$'],['pedidos_expedidos','Pedidos expedidos da mesma base',''],['itens_auditados','Itens / SKUs auditados',''],['itens_conformes','Itens / SKUs sem divergência',''],['estoque_fisico','Quantidade física contada','un.'],['estoque_registrado','Quantidade registrada comparável','un.']]}
];
const formatar=(v:number,u:string)=>u==='R$'?v.toLocaleString('pt-BR',{style:'currency',currency:'BRL'}):v.toLocaleString('pt-BR',{maximumFractionDigits:2})+' '+u;
const CORES:Record<string,string>={'Dentro da meta':'text-emerald-800 bg-emerald-50','Em alerta':'text-amber-900 bg-amber-50','Fora da meta':'text-red-800 bg-red-50','Sem dados':'text-slate-600 bg-slate-50'};

export default function DashboardSemanal({empresaId,resultados,turmaId,somenteLeitura=false}:{empresaId:number;resultados:Resultado[];turmaId?:number;somenteLeitura?:boolean}){
 const [rodada,setRodada]=useState(0),[area,setArea]=useState('marketing'),[vista,setVista]=useState('indicadores'),[pagina,setPagina]=useState(0);
 const [dados,setDados]=useState<Dados|null>(null),[bases,setBases]=useState<Record<string,number>>({}),[metas,setMetas]=useState<Record<string,Meta>>({});
 const [mensagem,setMensagem]=useState(''),[ocupado,setOcupado]=useState(false);
 const versao=useRef(0),r=resultados.find(x=>x.rodada===rodada)??resultados[resultados.length-1],n=r?.rodada;
 const rota=n?turmaId?`/api/professor/turmas/${turmaId}/empresas/${empresaId}/dashboard/${n}`:`/api/aluno/empresas/${empresaId}/dashboard/${n}`:'';
 useEffect(()=>{
  const v=++versao.current;setDados(null);setMensagem('');
  if(!rota)return;
  api.get<Dados>(rota).then(d=>{if(v===versao.current){setDados(d);setBases(d.bases);setMetas(d.metas??{});}}).catch(e=>{if(v===versao.current)setMensagem(e.message);});
  return()=>{versao.current++;};
 },[rota]);
 const alterado=!!dados&&(JSON.stringify(bases)!==JSON.stringify(dados.bases)||JSON.stringify(metas)!==JSON.stringify(dados.metas??{}));
 async function salvar(){
  if(Object.values(metas).some(m=>m.alvo==null||m.alerta==null)){setMensagem('Preencha a meta e o limite de alerta, ou remova essa meta.');return;}
  const v=versao.current;setOcupado(true);
  try{const d=await api.put<Dados>(rota,{...bases,metas});if(v===versao.current){setDados(d);setBases(d.bases);setMetas(d.metas??{});setMensagem('Análise salva. Resultados e notas do motor permanecem preservados.');}}
  catch(e){if(v===versao.current)setMensagem(e instanceof Error?e.message:'Erro ao salvar.');}
  finally{setOcupado(false);}
 }
 const atual=AREAS.find(a=>a.id===area)!;
 const itens=Object.entries(dados?.indicadores[area]??{}).filter(([k])=>area!=='producao'||!['Produção planejada','Produção realizada'].includes(k));
 const metasArea=itens.filter(([nome])=>dados?.direcoes?.[area]?.[nome]);
 const quantidade=vista==='metas'?metasArea.length:vista==='bases'?atual.campos.length:itens.length;
 const tamanho=vista==='metas'?1:4;
 const titulo=(x:Resultado)=>{const c=x.detalhes_simulacao?.calendario;return c?`Semana ${c.semana_iso}/${c.ano_iso} · ${c.inicio} a ${c.fim} · R${x.rodada}`:`Rodada ${x.rodada} · histórico mensal`};
 function mudarMeta(chave:string,campo:'alvo'|'alerta',valor:string){setMetas(antes=>{const prox={...antes},m={...prox[chave]};if(valor==='')delete m[campo];else m[campo]=Number(valor);if(m.alvo==null&&m.alerta==null)delete prox[chave];else prox[chave]=m;return prox;});}
 return <Cartao titulo="Painel semanal">
  <label>Semana / período registrado<select aria-label="Semana dos indicadores" className={estiloEntrada} value={n??''} onChange={e=>{if(alterado){setMensagem('Salve ou descarte suas alterações antes de trocar a semana.');return;}setRodada(Number(e.target.value));setPagina(0);}} disabled={ocupado}>{resultados.map(x=><option key={x.rodada} value={x.rodada}>{titulo(x)}</option>)}</select></label>
  {!r?<p className="mt-3">Disponível após o fechamento da primeira rodada.</p>:<>
   <nav className="etapas-curtas mt-3" aria-label="Áreas do painel semanal">{AREAS.map(a=><button key={a.id} aria-pressed={area===a.id} onClick={()=>{setArea(a.id);setPagina(0);setMensagem('');if(vista==='grafico')setVista('indicadores');if(!turmaId)api.post(`/api/aluno/empresas/${empresaId}/acessos`,{aba:`dashboard-semanal-${a.id}`}).catch(()=>undefined);}}>{a.nome}</button>)}</nav>
   <nav className="etapas-curtas" aria-label="Modo do painel">{[{id:'indicadores',nome:'Indicadores'},{id:'bases',nome:'Bases informadas'},{id:'metas',nome:'Metas'},...(area==='producao'?[{id:'grafico',nome:'Plano x realizado'}]:[])].map(v=><button key={v.id} aria-pressed={vista===v.id} onClick={()=>{setVista(v.id);setPagina(0);setMensagem('');}}>{v.nome}</button>)}</nav>
   {mensagem&&<p role="status" className="my-2 text-sm">{mensagem}</p>}
   {!dados&&!mensagem&&<p>Carregando…</p>}
   {dados&&vista==='indicadores'&&<div className="grid grid-cols-2 gap-3">{itens.slice(pagina*4,pagina*4+4).map(([nome,d])=><article key={nome} className="rounded-lg border border-slate-200 p-3">
    <h3 className="text-sm font-semibold">{nome}</h3><p className="my-1 text-xl font-bold">{d.valor==null?d.estado==='Não se aplica'?'Não se aplica':'Dados indisponíveis':formatar(d.valor,d.unidade)}</p>
    <p hidden={d.valor==null} className="text-xs text-slate-500">{d.estado}</p>
    {d.meta&&<div className="mt-1 text-xs"><span className={`inline-block rounded px-2 py-1 ${CORES[d.meta.status]}`}>{d.meta.status}</span><span className="ml-2">Meta {d.meta.direcao==='MAIOR'?'≥':'≤'} {formatar(d.meta.alvo!,d.unidade)}</span></div>}
   </article>)}</div>}
   {dados&&vista==='bases'&&<>
    <p className="my-2 text-xs text-slate-500">Dados informados pela equipe para análise, sem alterar vendas, caixa ou notas. Use a mesma semana, unidade e população. Horas realizadas não são horas planejadas.</p>
    <div className="grid gap-3 sm:grid-cols-2">{atual.campos.slice(pagina*4,pagina*4+4).map(([k,nome,unidade])=><label key={k} className="text-sm">{nome}<div className="flex items-center gap-2">{unidade==='R$'&&<span>R$</span>}<input aria-label={nome} className={estiloEntrada} disabled={somenteLeitura||ocupado} type="number" min={0} step={unidade?'any':1} value={bases[k]??''} placeholder="Não informado" onChange={e=>setBases(b=>{const prox={...b};if(e.target.value==='')delete prox[k];else prox[k]=Number(e.target.value);return prox;})}/>{unidade&&unidade!=='R$'&&<span>{unidade}</span>}</div></label>)}</div>
   </>}
   {dados&&vista==='metas'&&<>
    <p className="my-2 text-xs text-slate-500">Metas de comparação escolhidas pela equipe para esta semana. Não alteram a nota. O alerta é o limite da faixa intermediária; não há metas presumidas.</p>
    {metasArea.slice(pagina,pagina+1).map(([nome,d])=>{const chave=`${area}.${nome}`,m=metas[chave]??{},direcao=dados.direcoes[area][nome];return <fieldset key={nome} className="mb-3 rounded border p-2"><legend className="px-1 text-sm font-semibold">{nome} · {direcao==='MAIOR'?'maior é melhor':'menor é melhor'}</legend><div className="grid grid-cols-2 gap-3">{(['alvo','alerta'] as const).map(k=><label key={k} className="text-xs">{k==='alvo'?'Meta':'Limite de alerta'} {d.unidade&&`(${d.unidade})`}<input aria-label={`${nome}: ${k==='alvo'?'Meta':'Limite de alerta'}`} className={estiloEntrada} type="number" step="any" disabled={somenteLeitura||ocupado} value={m[k]??''} placeholder="Sem meta" onChange={e=>mudarMeta(chave,k,e.target.value)}/></label>)}</div>{!somenteLeitura&&<button type="button" className="mt-1 text-xs underline" disabled={ocupado} onClick={()=>setMetas(m=>{const prox={...m};delete prox[chave];return prox;})}>Remover meta</button>}</fieldset>;})}
   </>}
   {dados&&vista==='grafico'&&<div role="img" aria-label="Comparação da produção planejada e realizada">{['Produção planejada','Produção realizada'].map((k,i)=>{const v=dados.indicadores.producao[k]?.valor;const max=Math.max(1,...['Produção planejada','Produção realizada'].map(j=>dados.indicadores.producao[j]?.valor??0));return <div key={k} className="my-5 text-sm"><p>{k}: {v==null?'Dados indisponíveis':formatar(v,'un.')}</p>{v!=null&&<div style={{width:`${v/max*100}%`,height:18,background:i?'#0AADBF':'#034AA6'}}/>}</div>;})}</div>}
   {dados&&vista!=='grafico'&&quantidade>tamanho&&<nav className="mt-3 flex justify-between text-sm"><button disabled={!pagina} onClick={()=>setPagina(pagina-1)}>← Anterior</button><span>Página {pagina+1} de {Math.ceil(quantidade/tamanho)}</span><button disabled={(pagina+1)*tamanho>=quantidade} onClick={()=>setPagina(pagina+1)}>Próxima →</button></nav>}
   {dados&&!somenteLeitura&&(vista==='bases'||vista==='metas'||alterado)&&<div className="mt-3 flex items-center gap-3"><button className="rounded bg-marinho px-4 py-2 text-sm text-white" onClick={salvar} disabled={ocupado||!alterado}>Salvar análise da semana</button>{alterado&&<button className="text-sm underline" disabled={ocupado} onClick={()=>{setBases(dados.bases);setMetas(dados.metas??{});setMensagem('');}}>Descartar alterações</button>}</div>}
  </>}
 </Cartao>;
}
