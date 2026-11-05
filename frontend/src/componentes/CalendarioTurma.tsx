import {useState} from 'react';
import type {Turma} from '../tipos';
import {api} from '../api';
import {Aviso,Botao,Campo,Cartao,estiloEntrada} from './ui';

const DIAS=['Segunda-feira','Terça-feira','Quarta-feira','Quinta-feira','Sexta-feira','Sábado','Domingo'];
const hoje=new Date().toLocaleDateString('en-CA',{timeZone:'America/Sao_Paulo'});

function dataHora(valor:string){return new Date(valor).toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short',timeZone:'America/Sao_Paulo'});}

export default function CalendarioTurma({turma,aoSalvar}:{turma:Turma;aoSalvar:()=>void}){
 const [inicio,setInicio]=useState(turma.agenda_academica?.inicio_letivo??hoje);
 const [fim,setFim]=useState(turma.agenda_academica?.fim_letivo??'');
 const [dia,setDia]=useState(String(turma.agenda_academica?.dia_semana??0));
 const [horario,setHorario]=useState(turma.agenda_academica?.horario_inicio??'19:00');
 const [recessos,setRecessos]=useState((turma.agenda_academica?.recessos??[]).join(', '));
 const [erro,setErro]=useState<string|null>(null); const [salvando,setSalvando]=useState(false);
 const agenda=turma.agenda_academica;
 async function salvar(e:React.FormEvent){e.preventDefault();setErro(null);setSalvando(true);try{
   const lista=recessos.split(',').map(x=>x.trim()).filter(Boolean);
   await api.put(`/api/professor/turmas/${turma.id}/agenda-academica`,{inicio_letivo:inicio,fim_letivo:fim,dia_semana:Number(dia),horario_inicio:horario,recessos:lista});
   await aoSalvar();
 }catch(e){setErro(e instanceof Error?e.message:'Não foi possível programar as rodadas.');}finally{setSalvando(false);}}
 return <div className="space-y-4"><Cartao titulo="Programação acadêmica das rodadas">
   <p className="mb-4 text-sm text-slate-600">Informe uma vez o período da disciplina e o encontro semanal que marca cada rodada. O SempreHub abre a rodada na aula indicada e fecha automaticamente no início da próxima aula. O calendário econômico continua semanal e acompanha essas datas.</p>
   <form onSubmit={salvar} className="grid gap-4 md:grid-cols-2">
    <Campo rotulo="Início do período letivo"><input required type="date" className={estiloEntrada} value={inicio} onChange={e=>setInicio(e.target.value)}/></Campo>
    <Campo rotulo="Fim do período letivo"><input required type="date" min={inicio} className={estiloEntrada} value={fim} onChange={e=>setFim(e.target.value)}/></Campo>
    <Campo rotulo="Dia que marca a rodada"><select className={estiloEntrada} value={dia} onChange={e=>setDia(e.target.value)}>{DIAS.map((nome,i)=><option key={nome} value={i}>{nome}</option>)}</select></Campo>
    <Campo rotulo="Horário de abertura"><input required type="time" className={estiloEntrada} value={horario} onChange={e=>setHorario(e.target.value)}/></Campo>
    <div className="md:col-span-2"><Campo rotulo="Recessos e feriados sem aula" ajuda="Opcional. Informe datas separadas por vírgula no formato AAAA-MM-DD."><input className={estiloEntrada} placeholder="2027-04-21, 2027-05-01" value={recessos} onChange={e=>setRecessos(e.target.value)}/></Campo></div>
    {erro&&<div className="md:col-span-2"><Aviso>{erro}</Aviso></div>}
    <div className="md:col-span-2 flex justify-end"><Botao type="submit" carregando={salvando}>Programar todas as rodadas</Botao></div>
   </form>
 </Cartao>
 {agenda&&<Cartao titulo="Cronograma confirmado"><p className="text-sm">Encontro de referência: <strong>{agenda.dia_descricao}, {agenda.horario_inicio}</strong>. As datas abaixo são automáticas e podem ser revistas antes de existirem decisões na rodada atual.</p><div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th>Rodada</th><th>Abre</th><th>Fecha</th></tr></thead><tbody>{agenda.rodadas.map(item=><tr key={item.rodada} className={item.rodada===turma.rodada_atual?'font-semibold text-marinho':''}><td>{item.rodada}</td><td>{dataHora(item.abre_em)}</td><td>{dataHora(item.fecha_em)}</td></tr>)}</tbody></table></div></Cartao>}
 </div>;
}
