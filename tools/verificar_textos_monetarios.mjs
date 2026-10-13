import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url);
const ts=require('../frontend/node_modules/typescript');
const erros=[];
function conferir(arquivo){
 const fonte=ts.createSourceFile(arquivo,fs.readFileSync(arquivo,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 function visitar(node){
  if((ts.isStringLiteral(node)||ts.isNoSubstitutionTemplateLiteral(node)||node.kind===ts.SyntaxKind.TemplateHead||node.kind===ts.SyntaxKind.TemplateMiddle||node.kind===ts.SyntaxKind.TemplateTail) && /<ValorMonetario\b/.test(node.text)){
   const pos=fonte.getLineAndCharacterOfPosition(node.getStart(fonte));erros.push(`${arquivo}:${pos.line+1}: componente monetário dentro de texto literal`);
  }
  ts.forEachChild(node,visitar);
 }
 visitar(fonte);
}
function percorrer(dir){for(const item of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,item.name);if(item.isDirectory())percorrer(p);else if(/\.tsx?$/.test(p))conferir(p);}}
percorrer(path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../frontend/src'));
if(erros.length){console.error(erros.join('\n'));process.exit(1);}
console.log('Nenhum componente monetário foi inserido em texto literal.');
