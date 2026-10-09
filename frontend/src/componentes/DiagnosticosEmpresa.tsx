import React,{useState,useEffect} from "react";
import AnaliseConcorrencia,{type PerfilConcorrente} from "./AnaliseConcorrencia";
import {api} from "../api";
import {ResumoAnalises,analisesIniciais,type AnalisesEstrategicas} from "./FerramentasEstrategicas";
export default function DiagnosticosEmpresa({turmaId,empresaId}:{turmaId:number;empresaId:number}){
 const [dados,setDados]=useState<{id:number;rodada:number;dados:Partial<AnalisesEstrategicas>&{concorrentes?:PerfilConcorrente[];data_consulta?:string;fontes_pesquisa?:string[]}}[]>([]),[erro,setErro]=useState('');
 useEffect(()=>{api.get<typeof dados>(`/api/professor/turmas/${turmaId}/empresas/${empresaId}/diagnosticos`).then(setDados).catch(e=>setErro(e.message));},[turmaId,empresaId]);
 return <section><h3 className="mb-3 font-bold">Diagnósticos preparados pelo sistema</h3>{erro&&<p role="alert">{erro}</p>}{!dados.length&&!erro&&<p className="text-sm">Os diagnósticos são preparados automaticamente quando a equipe abre Ferramentas e segmentação.</p>}{dados.map(d=><article key={d.id}><ResumoAnalises rodada={d.rodada} valor={{...analisesIniciais(),...d.dados,diagnostico_automatico:true}}/><AnaliseConcorrencia concorrentes={d.dados.concorrentes||[]} plano={{produtos:[]}} data={d.dados.data_consulta}/><details className="my-4"><summary>Fontes da pesquisa · rodada {d.rodada}</summary>{(d.dados.fontes_pesquisa||[]).filter(url=>/^https?:\/\//.test(url)).map(url=><p key={url} className="break-all text-sm"><a href={url} target="_blank" rel="noopener noreferrer">{url}</a></p>)}</details></article>)}</section>;
}
