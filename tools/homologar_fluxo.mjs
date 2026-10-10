import {createRequire} from 'node:module';
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium,request}=require(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const base='http://127.0.0.1:8000';const out='tmp/qa';fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,channel:'chrome'});
const erros=[];const stamp=Date.now();const evidencias=[];
const http=await request.newContext();
async function req(url,sessao,method='GET',data){const r=await http.fetch(base+url,{method,headers:sessao?{Authorization:'Bearer '+sessao.token}:{},...(data?{data}: {})});assert(r.ok(),`${method} ${url}: ${r.status()} ${await r.text()}`);return r.json();}

async function cadastro(nome,email,papel='ALUNO'){return req('/api/auth/cadastro',null,'POST',{nome,email,senha:'senha-qa-isolada',papel,...(papel==='PROFESSOR'?{codigo_docente:'qa-local-isolado'}:{})});}
const prof=await cadastro('Professor Homologação',`qa-prof-${stamp}@iffar.edu.br`,'PROFESSOR');
async function equipe(modo){
 const turma=await req('/api/professor/turmas',prof,'POST',{nome:`QA ${modo} ${stamp}`,modo_jogo:modo,modo_equipe:true,total_rodadas:4,caixa_inicial:20000,demanda_base_por_empresa:40});
 const alunos=[];for(let i=0;i<3;i++)alunos.push(await cadastro(`QA ${modo} ${i}`,`qa-${modo.toLowerCase()}-${stamp}-${i}@aluno.iffar.edu.br`));
 const entrada=await req('/api/aluno/turmas/entrar',alunos[0],'POST',{codigo:turma.codigo,nome_empresa:`Empresa QA ${modo}`,tipo_entrada_gem:'OPORTUNIDADE',classe_dornelas:'SERIAL',regime_tributario:'SIMPLES_NACIONAL'});
 const id=entrada.empresa.id;const painel=await req(`/api/aluno/empresas/${id}`,alunos[0]);
 for(const aluno of alunos.slice(1))await req('/api/aluno/equipes/entrar',aluno,'POST',{codigo:painel.equipe.codigo_convite});
 for(const aluno of alunos.slice(0,2))await req(`/api/aluno/empresas/${id}/lider`,aluno,'POST',{aluno_id:alunos[0].usuario.id,rodada:1});
 return {turma,id,alunos};
}
async function abrir(sessao,url){const ctx=await browser.newContext({viewport:{width:1440,height:1000}});await ctx.addInitScript(s=>{localStorage.setItem('semprehub.token',s.token);localStorage.setItem('semprehub.usuario',JSON.stringify(s.usuario));},sessao);const p=await ctx.newPage();p.on('pageerror',e=>erros.push(e.message));await p.goto(base+url);await p.waitForLoadState('networkidle');return p;}
async function fecharAvisos(page){await page.waitForTimeout(250);for(let i=0;i<3 && await page.getByRole('dialog').count();i++){await page.getByRole('dialog').getByRole('button',{name:'Fechar',exact:true}).click();await page.waitForTimeout(100);}}
async function menus(page){await fecharAvisos(page);const botoes=page.locator('button[aria-controls^="secao-"]');const ids=await botoes.evaluateAll(xs=>xs.map(x=>x.getAttribute('aria-controls')));for(const id of [...new Set(ids)]){await page.locator(`button[aria-controls="${id}"]`).first().click();await page.waitForTimeout(80);assert.equal(await page.locator('[id^="secao-"]:visible').count(),1,'Painel duplicado em '+id);}evidencias.push(`Menus: ${ids.length} submenus conferidos`);}
const anon=await browser.newPage();await anon.goto(base);assert.equal(await anon.getByText('Manuais',{exact:true}).count(),0);for(const nome of ['aluno','professor','midias'])assert.equal((await anon.request.get(base+`/manuais/manual-${nome}.pdf`)).status(),401);
for(const modo of ['TRADICIONAL','STARTUP']){
 console.log('Homologando '+modo);const e=await equipe(modo);const lider=await abrir(e.alunos[0],`/#/empresa/${e.id}`);const membro=await abrir(e.alunos[1],`/#/empresa/${e.id}`);
 await lider.getByRole('button',{name:'Produtos e marketing',exact:false}).first().click();await membro.getByRole('button',{name:'Produtos e marketing',exact:false}).first().click();
 const preco=lider.getByRole('slider',{name:'Preço de venda',exact:true});await preco.waitFor();assert(!(await preco.isDisabled()));assert(await membro.getByRole('slider',{name:'Preço de venda',exact:true}).isDisabled());
 await preco.evaluate(el=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,'123');el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));});const salvo=lider.waitForResponse(r=>r.url().endsWith(`/api/aluno/empresas/${e.id}/decisao`) && r.request().method()==='PUT');await lider.getByRole('button',{name:'Salvar rascunho',exact:true}).click();assert((await salvo).ok());
 await lider.reload();await lider.getByRole('button',{name:'Produtos e marketing',exact:false}).first().click();assert.equal(await lider.getByRole('slider',{name:'Preço de venda',exact:true}).inputValue(),'123');
 await membro.reload();await membro.getByRole('button',{name:'Produtos e marketing',exact:false}).first().click();assert.equal(await membro.getByRole('slider',{name:'Preço de venda',exact:true}).inputValue(),'123');
 await lider.getByRole('button',{name:'Enviar decisão final',exact:true}).click();await lider.getByRole('button',{name:'Confirmar envio final',exact:true}).click();await lider.getByText(/Você não pode enviar/).first().waitFor();
 const painel=await req(`/api/aluno/empresas/${e.id}`,e.alunos[0]);
 const completa={rodada:1,versao:painel.equipe.versao_decisao,rascunho:false,preco:123,marketing:0,pd:0,networking:0,contratar:3,demitir:0,emprestimo:0,amortizacao:0,analise_financeira:'Comparar margem, custos, estoque e caixa antes de expandir.',revisao_areas:{decisoes:true,financas:true,producao:true,logistica:true},simulacao:{producao:100,comprar_mp:100,manutencao:1000,treinamento:300,salario:2100,beneficio:150,horas_extras:0,modal:'PADRAO',capacidade_nuvem:100}};
 await req(`/api/aluno/empresas/${e.id}/decisao`,e.alunos[0],'PUT',{...completa,rascunho:true});await lider.reload();await lider.getByRole('button',{name:'Produtos e marketing',exact:false}).first().click();await lider.getByRole('button',{name:'Enviar decisão final',exact:true}).click();const enviado=lider.waitForResponse(r=>r.url().endsWith(`/api/aluno/empresas/${e.id}/decisao`) && r.request().method()==='PUT');await lider.getByRole('button',{name:'Confirmar envio final',exact:true}).click();assert((await enviado).ok());
 for(const p of [lider,membro]){await p.reload();await p.getByRole('button',{name:'Produtos e marketing',exact:false}).first().click();await p.getByText(/Decisões salvas! Modo de leitura ativado/).waitFor();assert(await p.getByRole('slider',{name:'Preço de venda',exact:true}).isDisabled());}
 const resposta=await req(`/api/professor/turmas/${e.turma.id}/fechar-rodada`,prof,'POST',{rodada:1,forcar:true,evento:'NENHUM'});assert.equal(resposta.turma.rodada_atual,2);
 const resultado=(await req(`/api/aluno/empresas/${e.id}`,e.alunos[0])).resultados[0];assert.equal(resultado.engine_version,'2.0.0-deterministic-indicators');assert(resultado.detalhes_simulacao.operacao.enps>0);
 await lider.reload();await menus(lider);await lider.getByRole('button',{name:/Manuais · baixar PDF/}).click();assert.equal(await lider.getByRole('link',{name:/Baixar PDF:/}).count(),2);
 const docente=await abrir(prof,`/#/turma/${e.turma.id}`);await menus(docente);await docente.getByRole('button',{name:/Manuais · baixar PDF/}).click();assert.equal(await docente.getByRole('link',{name:/Baixar PDF:/}).count(),3);
 for(const page of [lider,docente]){const links=page.getByRole('link',{name:/Baixar PDF:/});for(let i=0;i<await links.count();i++){const baixa=page.waitForEvent('download');await links.nth(i).click();assert.equal(await (await baixa).failure(),null);}}
 const popupPromise=docente.waitForEvent('popup');const abriu=docente.waitForResponse(r=>r.url().endsWith('/api/manuais/manual-professor.pdf'));await docente.getByRole('link',{name:'Visualizar: Manual do professor',exact:true}).click();assert.equal((await abriu).status(),200);const preview=await popupPromise;await preview.waitForURL(url=>url.protocol==='blob:');await preview.close();
 await lider.getByRole('button',{name:/Histórico/,exact:false}).first().click();await lider.screenshot({path:`${out}/${modo.toLowerCase()}-historico.png`,fullPage:true});
 // Segunda rodada extrema: produção zero, sem funcionários e caixa em déficit.
 const atual=await req(`/api/aluno/empresas/${e.id}`,e.alunos[0]);await req(`/api/aluno/empresas/${e.id}/decisao`,e.alunos[0],'PUT',{...completa,rodada:2,versao:atual.equipe.versao_decisao,contratar:0,demitir:atual.empresa.funcionarios,marketing:100000,simulacao:{...completa.simulacao,producao:0,comprar_mp:0,manutencao:0,treinamento:0,beneficio:0,capacidade_nuvem:0}});
 await req(`/api/professor/turmas/${e.turma.id}/fechar-rodada`,prof,'POST',{rodada:2,forcar:true,evento:'NENHUM'});
 const final=await req(`/api/aluno/empresas/${e.id}`,e.alunos[0]);const r=final.resultados.at(-1);assert(r.caixa_final<0);assert.equal(r.detalhes_simulacao.balanco.disponibilidades,0);assert.equal(r.detalhes_simulacao.balanco.cheque_especial,-r.caixa_final);assert.equal(r.detalhes_simulacao.operacao.oee,null);assert.equal(r.detalhes_simulacao.operacao.enps,null);
 assert.deepEqual(final.resultados[0],resultado);await lider.reload();await fecharAvisos(lider);await lider.getByRole('button',{name:'Produção',exact:true}).last().click();await lider.locator('[id^="secao-"]:visible').getByText('Não se aplica',{exact:true}).first().waitFor();
 await lider.getByRole('button',{name:'Recursos humanos',exact:true}).last().click();await lider.locator('[id^="secao-"]:visible').getByText('Não se aplica',{exact:true}).first().waitFor();
 await lider.getByRole('button',{name:'DRE e balanço',exact:true}).first().click();await lider.getByText('Ver balanço e demonstrativos completos',{exact:true}).click();await lider.locator('[id^="secao-"]:visible').getByText('Cheque especial',{exact:true}).waitFor();await lider.screenshot({path:`${out}/${modo.toLowerCase()}-balanco.png`,fullPage:true});
 evidencias.push(`${modo}: rascunho persistido, membro bloqueado, envio incompleto rejeitado, envio final bloqueado, duas rodadas, eNPS positivo, zero funcionários/produção, déficit reclassificado, histórico preservado, downloads e menus`);
}
assert.deepEqual(erros,[]);fs.writeFileSync(out+'/homologacao.json',JSON.stringify({aprovado:true,evidencias,erros},null,2));await http.dispose();await browser.close();console.log(JSON.stringify({aprovado:true,evidencias}));
