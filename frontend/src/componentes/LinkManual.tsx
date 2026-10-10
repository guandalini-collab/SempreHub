import React,{useState} from 'react';
import {baixarArquivo,visualizarArquivo} from '../api';
export default function LinkManual({arquivo,baixar=false,children,...props}:{arquivo:string;baixar?:boolean;children:React.ReactNode}&Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>,'href'|'onClick'>) {
 const [erro,setErro]=useState('');
 return <><a {...props} href={`/api/manuais/${arquivo}.pdf`} onClick={async e=>{e.preventDefault();setErro('');try {if(baixar)await baixarArquivo(`/api/manuais/${arquivo}.pdf`,`SempreHub-${arquivo}.pdf`);else await visualizarArquivo(`/api/manuais/${arquivo}.pdf`);}catch(e){setErro(e instanceof Error?e.message:'Não foi possível abrir o manual.');}}}>{children}</a>{erro&&<span role="alert" className="text-sm text-red-700">{erro}</span>}</>;
}
