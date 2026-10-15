import React,{useState} from 'react';
import type {Turma} from '../tipos';
import {api} from '../api';
import {Botao,Cartao,estiloEntrada} from './ui';
import {tituloPeriodo,dataCurta} from '../calendario';
export default function CalendarioTurma({turma,aoSalvar}:{turma:Turma;aoSalvar:()=>void}){
 const [data,setData]=useState('');const [perfil,setPerfil]=useState('NEUTRO');const [erro,setErro]=useState('');const [ocupado,setOcupado]=useState(false);
 const c=turma.calendario;
 async function salvar(){setOcupado(true);setErro('');try{await api.put(`/api/professor/turmas/${turma.id}/calendario`,{data_inicio:data,perfil_sazonal:perfil});aoSalvar();}catch(e){setErro(e instanceof Error?e.message:'Não foi possível salvar.');}finally{setOcupado(false);}}
 return <Cartao titulo="Calendário simulado">{c?<><p className="font-semibold">{tituloPeriodo(c)}</p><p className="mt-2 text-sm">Sazonalidade: {c.sazonalidade.perfil} · {c.sazonalidade.eventos.join(', ')||'sem evento sazonal'} · fator de procura {c.sazonalidade.demanda.toFixed(2)}. Estimativa do Modelo.</p><p className="mt-2 text-sm">Próximas datas: {c.proximos_eventos.map(e=>`${e.nome}: ${dataCurta(e.data)}`).join(' · ')||'sem datas nos próximos 90 dias'}.</p></>:<><p className="mb-3 text-sm">Ativar semanas de sete dias a partir da rodada {turma.rodada_atual}. O histórico mensal será preservado. Defina antes de salvar decisões. O prazo real de envio continua separado.</p><div className="grid gap-3 sm:grid-cols-2"><label>Primeiro dia simulado<input type="date" required className={estiloEntrada} value={data} onChange={e=>setData(e.target.value)}/></label><label>Perfil de sazonalidade<select className={estiloEntrada} value={perfil} onChange={e=>setPerfil(e.target.value)}><option value="NEUTRO">Neutro</option><option value="VAREJO">Varejo</option><option value="ALIMENTACAO">Alimentação</option><option value="SERVICOS">Serviços</option></select></label></div><div className="mt-3"><Botao disabled={!data||ocupado||turma.modo_jogo==='LEGADO'} onClick={salvar}>Ativar calendário semanal</Botao></div>{erro&&<p role="alert">{erro}</p>}</>}</Cartao>;
}
