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
 const [horario,setHorario]=useState(turma.agenda_academica?.horario_inicio??'19:30');
 const [termino,setTermino]=useState(turma.agenda_academica?.horario_fim??'21:30');
 const [recessos,setRecessos]=useState((turma.agenda_academica?.recessos??[]).join(', '));
 const [erro,setErro]=useState<string|null>(null); const [salvando,setSalvando]=useState(false);
 const agenda=turma.agenda_academica;
 const [rodadaExt,setRodadaExt]=useState(String(turma.rodada_atual));
 const [dataExt,setDataExt]=useState(''); const [horaExt,setHoraExt]=useState('23:59');
 const [msgExt,setMsgExt]=useState<string|null>(null);
 async function estender(cancelar=false){setMsgExt(null);setSalvando(true);try{
   await api.put(`/api/professor/turmas/${turma.id}/prorrogacao`,cancelar?{rodada:Number(rodadaExt)}:{rodada:Number(rodadaExt),data:dataExt,horario:horaExt});
   setMsgExt(cancelar?'Extensão cancelada: a rodada volta a fechar no término da aula.':'Fechamento estendido. As rodadas seguintes abrem na primeira aula depois dele.');
   await aoSalvar();
 }catch(e){setMsgExt(e instanceof Error?e.message:'Não foi possível estender o fechamento.');}finally{setSalvando(false);}}
 async function salvar(e:React.FormEvent){e.preventDefault();setErro(null);setSalvando(true);try{
   const lista=recessos.split(',').map(x=>x.trim()).filter(Boolean);
   await api.put(`/api/professor/turmas/${turma.id}/agenda-academica`,{inicio_letivo:inicio,fim_letivo:fim,dia_semana:Number(dia),horario_inicio:horario,horario_fim:termino,recessos:lista});
   await aoSalvar();
 }catch(e){setErro(e instanceof Error?e.message:'Não foi possível programar as rodadas.');}finally{setSalvando(false);}}
 return <div className="space-y-4"><Cartao titulo="Programação acadêmica das rodadas">
   <p className="mb-4 text-sm text-slate-600">Informe uma vez o período da disciplina e o horário da aula. Cada rodada fica aberta só durante a aula (no máximo 2 horas) e fecha automaticamente no horário de término; fora dessa janela os alunos apenas consultam os resultados. Em turmas com equipes, a rodada 1 começa na primeira aula depois que você encerrar a formação. Cada rodada corresponde a um mês de operação, a partir do mês da primeira aula de decisão.</p>
   <form onSubmit={salvar} className="grid gap-4 md:grid-cols-2">
    <Campo rotulo="Início do período letivo"><input required type="date" className={estiloEntrada} value={inicio} onChange={e=>setInicio(e.target.value)}/></Campo>
    <Campo rotulo="Fim do período letivo"><input required type="date" min={inicio} className={estiloEntrada} value={fim} onChange={e=>setFim(e.target.value)}/></Campo>
    <Campo rotulo="Dia da aula"><select className={estiloEntrada} value={dia} onChange={e=>setDia(e.target.value)}>{DIAS.map((nome,i)=><option key={nome} value={i}>{nome}</option>)}</select></Campo>
    <Campo rotulo="Início da aula (abertura da rodada)"><input required type="time" className={estiloEntrada} value={horario} onChange={e=>setHorario(e.target.value)}/></Campo>
    <Campo rotulo="Término da aula (fechamento automático)" ajuda="No máximo 2 horas depois do início."><input required type="time" className={estiloEntrada} value={termino} onChange={e=>setTermino(e.target.value)}/></Campo>
    <div className="md:col-span-2"><Campo rotulo="Recessos e feriados sem aula" ajuda="Opcional. Informe datas separadas por vírgula no formato AAAA-MM-DD."><input className={estiloEntrada} placeholder="2027-04-21, 2027-05-01" value={recessos} onChange={e=>setRecessos(e.target.value)}/></Campo></div>
    {erro&&<div className="md:col-span-2"><Aviso>{erro}</Aviso></div>}
    <div className="md:col-span-2 flex justify-end"><Botao type="submit" carregando={salvando}>Programar todas as rodadas</Botao></div>
   </form>
 </Cartao>
 {agenda&&<Cartao titulo="Estender o fechamento de uma rodada (opcional)">
   <p className="mb-4 text-sm text-slate-600">Use só quando quiser deixar uma rodada aberta por mais tempo, por exemplo a aula 1, para os alunos se familiarizarem com a plataforma. A rodada abre normalmente no início da aula e fecha no dia e horário escolhidos (horário de Brasília). Ao fechar, ela é processada automaticamente; a rodada seguinte não abre na hora, e sim na primeira aula depois desse fechamento, com a janela normal da aula.</p>
   <div className="grid gap-4 md:grid-cols-3">
    <Campo rotulo="Rodada"><select className={estiloEntrada} value={rodadaExt} onChange={e=>setRodadaExt(e.target.value)}>{agenda.rodadas.map(item=><option key={item.rodada} value={item.rodada}>Rodada {item.rodada}</option>)}</select></Campo>
    <Campo rotulo="Estender até o dia"><input type="date" className={estiloEntrada} value={dataExt} onChange={e=>setDataExt(e.target.value)}/></Campo>
    <Campo rotulo="Horário do fechamento"><input type="time" className={estiloEntrada} value={horaExt} onChange={e=>setHoraExt(e.target.value)}/></Campo>
   </div>
   {msgExt&&<div className="mt-3"><Aviso tipo="info">{msgExt}</Aviso></div>}
   <div className="mt-4 flex flex-wrap justify-end gap-2">
    {!!agenda.prorrogacoes?.[rodadaExt]&&<Botao variante="secundario" carregando={salvando} onClick={()=>estender(true)}>Cancelar extensão desta rodada</Botao>}
    <Botao carregando={salvando} disabled={!dataExt||!horaExt} onClick={()=>estender()}>Estender o fechamento</Botao>
   </div>
 </Cartao>}
 {agenda&&<Cartao titulo="Cronograma confirmado"><p className="text-sm">Aula de referência: <strong>{agenda.dia_descricao}, {agenda.horario_inicio}{agenda.horario_fim?` às ${agenda.horario_fim}`:''}</strong>.{!turma.formacao_encerrada&&turma.modo_equipe?' As datas serão recalculadas quando a formação das equipes for encerrada.':''} As datas abaixo são automáticas e podem ser revistas antes de existirem decisões na rodada atual.</p><div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th>Rodada</th><th>Abre</th><th>Fecha</th></tr></thead><tbody>{agenda.rodadas.map(item=><tr key={item.rodada} className={item.rodada===turma.rodada_atual?'font-semibold text-marinho':''}><td>{item.rodada}</td><td>{dataHora(item.abre_em)}</td><td>{dataHora(item.fecha_em)}{item.prorrogada?' (estendida)':''}</td></tr>)}</tbody></table></div></Cartao>}
 </div>;
}
