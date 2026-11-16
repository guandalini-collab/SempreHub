export interface ProximoMes { inicio:string; mes:number; ano:number; fator:number; atividade_pmc:string|null; variacao:number; fonte:string; estado:string }
export interface CalendarioSimulado {
  periodicidade: 'SEMANAL'|'MENSAL_CALENDARIO'; inicio: string; fim: string; dias: number; fator_mensal: number;
  mes?: number; ano?: number; proximo_mes?: ProximoMes;
  semana_iso: number; ano_iso: number; ano_fiscal: number; semana_iso_fim?: number; ano_iso_fim?: number;
  meses: {data:string;peso_mensal:number}[];
  sazonalidade:{estado:string;perfil?:string;fonte?:string;atividade_pmc?:string|null;observacao?:string;periodo_base?:string|null;setor?:string|null;eventos:string[];demanda:number;insumos:number;frete:number;detalhes_eventos?:{nome:string;data:string;fase:string;impacto_demanda:number;orientacao:string;fonte:string}[]};
  proximos_eventos:{nome:string;data:string;impacto?:string;peso_setorial?:number}[];
}
export const dataCurta=(v:string)=>new Date(v+'T12:00:00').toLocaleDateString('pt-BR');
// A rodada dura 7 dias a partir da data ativa da turma; quando o intervalo
// atravessa duas semanas ISO, o rótulo mostra as duas.
export const rotuloSemanaIso=(c:Pick<CalendarioSimulado,'semana_iso'|'ano_iso'|'semana_iso_fim'|'ano_iso_fim'>)=>{
  const fim=c.semana_iso_fim??c.semana_iso, anoFim=c.ano_iso_fim??c.ano_iso;
  if(fim===c.semana_iso&&anoFim===c.ano_iso) return `Semana ISO ${c.semana_iso}/${c.ano_iso}`;
  return anoFim===c.ano_iso?`Semanas ISO ${c.semana_iso}–${fim}/${c.ano_iso}`:`Semanas ISO ${c.semana_iso}/${c.ano_iso}–${fim}/${anoFim}`;
};
export const nomeMes=(inicio:string)=>new Date(inicio+'T12:00:00').toLocaleDateString('pt-BR',{month:'long',year:'numeric'});
export const tituloPeriodo=(c?:CalendarioSimulado|null)=>!c?'Calendário mensal':c.periodicidade==='MENSAL_CALENDARIO'?`Mês de operação: ${nomeMes(c.inicio)}`:`${rotuloSemanaIso(c)} · ${dataCurta(c.inicio)} a ${dataCurta(c.fim)}`;

// Rateio por dia em centavos: semanas atravessam meses sem duplicar receitas ou despesas.
export function consolidarDres(resultados:import('./tipos').Resultado[], tipo:'mes'|'trimestre') {
 const grupos=new Map<string,{nome:string;dre:Record<string,number>;dias:Set<string>}>();
 for(const r of resultados){const c=r.detalhes_simulacao?.calendario;if(!c)continue;
  for(let i=0;i<c.dias;i++){
   const dia=c.meses[i].data,ano=dia.slice(0,4),mes=Number(dia.slice(5,7));
   const chave=tipo==='mes'?dia.slice(0,7):`${ano}-T${Math.ceil(mes/3)}`;
   if(!grupos.has(chave))grupos.set(chave,{nome:chave,dre:{},dias:new Set()});
   const g=grupos.get(chave)!;g.dias.add(dia);
   for(const [campo,valor] of Object.entries(r.dre)){if(typeof valor!=='number')continue;
    const centavos=Math.round(Math.abs(valor)*100),base=Math.floor(centavos/c.dias),resto=centavos%c.dias;
    g.dre[campo]=(g.dre[campo]??0)+(Math.sign(valor)*(base+(i<resto?1:0)))/100;
   }
  }
 }
 return [...grupos.values()].sort((a,b)=>a.nome.localeCompare(b.nome));
}
