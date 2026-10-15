import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const ts=require('../frontend/node_modules/typescript');
const compiled=ts.transpileModule(fs.readFileSync(new URL('../frontend/src/calendario.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
const api={};new Function('exports',compiled)(api);
const dias=['2026-12-29','2026-12-30','2026-12-31','2027-01-01','2027-01-02','2027-01-03','2027-01-04'];
const entrada=[{dre:{receita:100.01,juros:3.57,lucro_liquido:-25.17},detalhes_simulacao:{calendario:{dias:7,meses:dias.map(data=>({data}))}}}];
const antes=JSON.stringify(entrada);
for(const tipo of ['mes','trimestre']){const consolidado=api.consolidarDres(entrada,tipo);assert.equal(consolidado.length,2);for(const k of Object.keys(entrada[0].dre)){const soma=consolidado.reduce((v,g)=>v+g.dre[k],0);assert(Math.abs(soma-entrada[0].dre[k])<.00001);}assert.equal(consolidado[0].dias.size,3);assert.equal(consolidado[1].dias.size,4);}
assert.equal(JSON.stringify(entrada),antes);
assert.equal(api.consolidarDres([{dre:{receita:100},detalhes_simulacao:{}}],'mes').length,0);
console.log('Rateio mensal e trimestral, centavos, virada de ano e preservação do legado: aprovados.');
