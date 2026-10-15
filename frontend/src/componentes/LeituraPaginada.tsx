import React, { useState } from "react";

/** Mantém todo o texto acessível, em páginas curtas, sem resumi-lo. */
export default function LeituraPaginada({ texto }: { texto: string }) {
  const [pagina,setPagina] = useState(0);
  const palavras=texto.split(/\s+/).filter(Boolean), paginas:string[]=[];
  let trecho="";
  for(const palavra of palavras) { if(trecho.length+palavra.length>850) {paginas.push(trecho);trecho="";} trecho+=(trecho?" ":"")+palavra; }
  if(trecho) paginas.push(trecho);
  const atual=Math.min(pagina,Math.max(0,paginas.length-1));
  return <div><p className="my-3 text-sm leading-relaxed">{paginas[atual] ?? "Sem texto disponível."}</p>{paginas.length>1 && <nav aria-label="Páginas da leitura" className="etapas-curtas"><button type="button" disabled={!atual} onClick={()=>setPagina(atual-1)}>← Anterior</button><span className="self-center text-xs">Página {atual+1} de {paginas.length}</span><button type="button" disabled={atual+1>=paginas.length} onClick={()=>setPagina(atual+1)}>Próxima →</button></nav>}</div>;
}
