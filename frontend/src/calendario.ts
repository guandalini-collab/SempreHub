export interface CalendarioSimulado {
  periodicidade: 'SEMANAL'; inicio: string; fim: string; dias: number; fator_mensal: number;
  semana_iso: number; ano_iso: number; ano_fiscal: number;
  meses: {data:string;peso_mensal:number}[];
  sazonalidade:{estado:string;perfil:string;eventos:string[];demanda:number;insumos:number;frete:number};
  proximos_eventos:{nome:string;data:string}[];
}
export const dataCurta=(v:string)=>new Date(v+'T12:00:00').toLocaleDateString('pt-BR');
export const tituloPeriodo=(c?:CalendarioSimulado|null)=>c?`Semana ${c.semana_iso}/${c.ano_iso} · ${dataCurta(c.inicio)} a ${dataCurta(c.fim)}`:'Calendário mensal';

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
