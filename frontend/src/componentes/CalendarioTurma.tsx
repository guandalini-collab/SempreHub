import type {Turma} from '../tipos';
import {Cartao} from './ui';
import {tituloPeriodo,dataCurta} from '../calendario';
export default function CalendarioTurma({turma}:{turma:Turma;aoSalvar:()=>void}){
 const c=turma.calendario;
 return <Cartao titulo="Calendário automático">{c?<><p className="font-semibold">{tituloPeriodo(c)}</p><p className="mt-2 text-sm">O primeiro período começa na data de início da turma, pelo horário de Brasília. Cada rodada seguinte avança sete dias; recarregar a página não muda as datas.</p><p className="mt-2 text-sm">Sazonalidade: {c.sazonalidade.perfil} · {c.sazonalidade.eventos.join(', ')||'sem evento sazonal'} · fator de procura {c.sazonalidade.demanda.toFixed(2)}. Estimativa do Modelo.</p><p className="mt-2 text-sm">Próximas datas: {c.proximos_eventos.map(e=>`${e.nome}: ${dataCurta(e.data)}`).join(' · ')||'sem datas nos próximos 90 dias'}.</p></>:<p>O calendário semanal será iniciado automaticamente. Se esta rodada já possui decisões salvas, ela mantém suas regras; a transição ocorrerá na próxima rodada, preservando o histórico.</p>}<p className="mt-3 text-xs text-slate-500">Cenário didático PLP 186/2026: R$ 110 mil em 2027, R$ 140 mil a partir de 2028 e até dois empregados nas atividades abrangidas no âmbito rural. Proposta ainda não vigente, sujeita ao Senado, sanção e condições orçamentárias.</p></Cartao>;
}
