import React,{useState,useEffect} from "react";
import {api} from "../api";
import {ResumoAnalises,analisesIniciais,type AnalisesEstrategicas} from "./FerramentasEstrategicas";
export default function DiagnosticosEmpresa({turmaId,empresaId}:{turmaId:number;empresaId:number}){
 const [dados,setDados]=useState<{id:number;rodada:number;dados:Partial<AnalisesEstrategicas>}[]>([]),[erro,setErro]=useState('');
 useEffect(()=>{api.get<typeof dados>(`/api/professor/turmas/${turmaId}/empresas/${empresaId}/diagnosticos`).then(setDados).catch(e=>setErro(e.message));},[turmaId,empresaId]);
 return <section><h3 className="mb-3 font-bold">Diagnósticos preparados pelo sistema</h3>{erro&&<p role="alert">{erro}</p>}{!dados.length&&!erro&&<p className="text-sm">Os diagnósticos são preparados automaticamente quando a equipe abre Ferramentas e segmentação.</p>}{dados.map(d=><ResumoAnalises key={d.id} rodada={d.rodada} valor={{...analisesIniciais(),...d.dados,diagnostico_automatico:true}}/>)}</section>;
}
