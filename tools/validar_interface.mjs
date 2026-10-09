import {createRequire} from 'node:module';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
const require=createRequire(import.meta.url);
// Arquivos temporários ignorados pelo Git; os componentes e exemplos ficam versionados.
fs.writeFileSync("frontend/qa-manual.tsx", 'import "../tools/fixtures/manual";\n');
fs.writeFileSync("frontend/qa-manual.html", '<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="root"></div><script type="module" src="/qa-manual.tsx"></script></body></html>');
let playwright;try{playwright=require(process.env.PLAYWRIGHT_MODULE || 'playwright');}catch{playwright=require(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));}
const {chromium}=playwright;
const browser=await chromium.launch({headless:true,...(fs.existsSync('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')?{channel:'chrome'}:{})});
const page=await browser.newPage({viewport:{width:1120,height:1000},deviceScaleFactor:1.5});
const erros=[];page.on('pageerror',e=>erros.push(e.message));
const membros=[{aluno_id:1,nome:'Ana',cargos:['CEO']},{aluno_id:2,nome:'Bruno',cargos:[]},{aluno_id:3,nome:'Carla',cargos:[]}];
const turma={id:1,nome:'Marketing - exemplo',professor:'Professor',codigo:'EXEMPLO',visivel_ingresso:true,formacao_encerrada:false,status:'ABERTA',rodada_atual:1,total_rodadas:12,modo_jogo:'LEGADO',cenario:'ZERO',modo_equipe:true,quantidade_empresas:1,parametros:{modo_jogo:'LEGADO',modo_equipe:true,caixa_inicial:20000,preco_referencia:100,custo_unitario:40,demanda_base_por_empresa:220,produtividade_por_pessoa:120,custos_fixos_mensais:1500,salario_base:2000,taxa_juros_mensal:.025,taxa_cheque_especial:.08,limite_credito:50000,teto_mei_anual:81000,configuracao_simulacao:{concorrentes_virtuais:2,nivel_concorrencia:'MEDIA',estrutura_mercado:'CONCORRENCIA_MONOPOLISTICA',forca_concorrentes:'NORMAL'}}};
const equipe={codigo_convite:null,membros,meus_cargos:[],pode_gerenciar:true,pode_decidir:true,lider_id:1,proximo_lider_id:null,transferencia_rodada:null,votos_lider:{},versao_decisao:0,aprovacoes:[],aprovada_por_mim:false,pronta:false,pendencias:['O líder ainda não enviou a decisão final.'],historico:[]};
const empresa={id:1,nome:'Equipe exemplo',aluno:'Ana',aluno_id:1,tipo_entrada_gem:'OPORTUNIDADE',classe_dornelas:'SERIAL',regime_tributario:'MEI',regime_pretendido:null,fase_atual:'IDEACAO',caixa:20000,divida:0,funcionarios:0,marca:0,qualidade:0,patrimonio:20000,networking:20,autoeficacia:50,necessidade_realizacao:50,faturamento_ano:0,fator_clt:1.45,estado_simulacao:null};
let matricula=null,decisao=null;
const sala={formacao_encerrada:false,disponiveis:[{aluno_id:4,nome:'Daniela'},{aluno_id:5,nome:'Eduardo'}],equipes:[{empresa_id:1,nome:'Equipe exemplo',membros,vagas:2,completa:false}]};
await page.route('**/api/**',async route=>{
 const req=route.request(),path=new URL(req.url()).pathname;let data={},status=200;
 if(path==='/api/aluno/turmas') data=[turma];
 else if(path==='/api/aluno/empresas')data=[];
 else if(path==='/api/aluno/matricula'){if(req.method()==='POST')matricula={turma,sala};data=matricula;}
 else if(path==='/api/aluno/empresas/1/lider')data={...equipe,proximo_lider_id:2,transferencia_rodada:2};
 else if(path==='/api/aluno/empresas/1')data={empresa,turma,equipe:{...equipe,versao_decisao:decisao?.versao??0},decisao_atual:decisao,ultima_decisao:decisao,resultados:[],eventos:[],mercado:[],posicao_ranking:1,total_empresas:1,pendencias_envio:['Revise e confirme Finanças.','Preencha a análise financeira da equipe.']};
 else if(path.endsWith('/previsao'))data={rodada:1,regime:'MEI',funcionarios:0,capacidade:120,folha:0,juros:0,gastos_previstos:1500,margem_unitaria:60,ponto_equilibrio:25,emprestimo_aprovado:0,amortizacao_aplicada:0,divida_prevista:0,caixa_disponivel:20000,alertas:[]};
 else if(path.endsWith('/decisao')){const d=req.postDataJSON();if(!d.rascunho){status=422;data={detail:'Você não pode enviar a decisão final: Revise e confirme a área: Finanças. Preencha a análise financeira da equipe.'};}else{decisao={...d,rodada:1,versao:(decisao?.versao??0)+1,enviada_em:null,automatica:false};data=decisao;}}
 else if(path.endsWith('/mercado-real'))data={edicoes:[]};
 else if(path.endsWith('/relatorios-empresariais'))data=[];
 else if(path==='/api/educacao/referencias')data={referencias:[]};
 else if(path==='/api/educacao/campanhas'||path==='/api/educacao/manual-midias'||path==='/api/educacao/midias')data={midias:[]};
 else{status=404;data={detail:'Dados ainda não disponíveis.'};}
 await route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
});
fs.mkdirSync('docs/diagramas',{recursive:true});
const abrir=async modo=>{await page.goto('http://127.0.0.1:4173/qa-manual.html?modo='+modo);await page.waitForLoadState('networkidle');};
await abrir('ingresso');await page.getByRole('button',{name:/Marketing - exemplo/}).waitFor();await page.getByRole('heading',{name:'Turmas disponíveis'}).locator('xpath=ancestor::section[1]').screenshot({path:'docs/diagramas/ingresso-nome.png'});
await page.getByRole('button',{name:/Marketing - exemplo/}).click();await page.getByRole('heading',{name:'Colegas disponíveis'}).waitFor();await page.getByRole('heading',{name:'Forme sua equipe por afinidade'}).locator('xpath=ancestor::section[1]').screenshot({path:'docs/diagramas/formacao-afinidade.png'});
await abrir('equipe');await page.getByLabel('Integrante para liderança').selectOption('2');await page.locator('main').screenshot({path:'docs/diagramas/transferir-lider.png'});await page.getByRole('button',{name:'Transferir liderança para a próxima rodada'}).click();await page.getByText(/Próximo líder: Bruno/).waitFor();await page.locator('main').screenshot({path:'docs/diagramas/lider-proxima-rodada.png'});
await abrir('bcg');await page.getByRole('img',{name:/Matriz BCG/}).waitFor();await page.locator('main').screenshot({path:'docs/diagramas/matriz-bcg.png'});
await page.setViewportSize({width:390,height:900});await abrir('bcg');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));await page.setViewportSize({width:1120,height:1000});
await abrir('decisao');await page.getByRole('button',{name:'Produtos e marketing',exact:false}).first().click();await page.getByRole('button',{name:'Enviar decisão final',exact:true}).waitFor();await page.getByRole('button',{name:'Enviar decisão final',exact:true}).click();await page.getByText(/Você não pode enviar a decisão final:/).waitFor();await page.getByText(/Você não pode enviar a decisão final:/).screenshot({path:'docs/diagramas/envio-bloqueado.png'});
await page.getByRole('button',{name:'Salvar e ir para a próxima etapa →',exact:true}).click();await page.getByRole('heading',{name:/Ferramentas estratégicas e segmentação · mês/}).waitFor();assert(decisao&&decisao.enviada_em===null);
assert.deepEqual(erros,[],'Erros de execução na interface');
await browser.close();console.log('Interface conferida: ingresso, formação, liderança, BCG, bloqueio e rascunho com avanço.');
