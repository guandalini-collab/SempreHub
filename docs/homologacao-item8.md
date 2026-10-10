# Homologação do item 8 - SempreHub

Data: 10 de outubro de 2026. Situação: validação local antes da publicação. Nenhuma alteração foi enviada ao GitHub ou Railway nesta etapa.

## Ambiente e preservação

Backend FastAPI com banco SQLite exclusivo de QA e frontend compilado. Serviços de pesquisa/OpenAI e e-mail desativados no teste. Turmas novas e separadas para Tradicional e Startup; nenhum banco, turma ou equipe de produção foi acessado ou alterado. Os testes de histórico legado usam registros artificiais no banco isolado.

## Verificações e evidências

- Backend: 243 testes aprovados. Cinco avisos de descontinuação de dependências/eventos preexistentes, sem falha de execução.
- Frontend: TypeScript e build Vite aprovados.
- Navegação real: 38 itens do aluno e 18 do professor em cada modelo; um painel correspondente visível por submenu e nenhum erro de JavaScript. O painel de parâmetros recebeu a identificação estrutural que faltava para o vínculo com o menu.
- Rascunhos: preço alterado pelo líder, salvo, preservado após recarregar e visível no perfil do integrante. Integrantes bloqueados desde o início; envio incompleto rejeitado; envio final confirmado pela interface e decisões preservadas em modo leitura para ambos.
- Investimentos opcionais: envio aceito com anúncios, P&D, networking e crédito em zero, sem obrigar investimento.
- Dois fechamentos por modelo: avanço correto de rodada, versão nova registrada, eNPS positivo na combinação aprovada e ausência de funcionários tratada como Não se aplica. OEE sem produção planejada e operações industriais ausentes no Startup não recebem valor artificial.
- Cenário extremo: produção zero, desligamento da equipe e despesa de marketing superior ao caixa. Header e fluxo mantêm déficit; balanço mostra disponibilidades zero e cheque especial positivo. Resultado anterior permanece idêntico após a nova rodada.
- Prazos: antes do limite permitido; no limite de 23:59:59 de Brasília e após ele, bloqueio HTTP 403. Prazo vinculado à rodada; nenhum bloqueio diário indevido. Fechamentos manual e automático concorrentes produzem apenas um resultado e um avanço.
- PDFs: URLs atuais e antigas exigem autenticação; aluno acessa aluno/mídias, professor acessa os três. Manual docente negado ao aluno. Downloads pela interface conferidos em ambos os modelos; visualização autenticada abre nova aba. Nenhum menu de manuais na abertura pública.
- Documentação: aluno e professor edição 3.5, 39 e 33 páginas, respectivamente. Marca vetorial, diagrama, autoria, sumário e cores conceituais oficiais preservados; todos os indicadores incluem significado, fórmula e interpretação. Professor recebe também regras de versionamento e métodos de cálculo. Páginas renderizadas e examinadas; manual de mídias preservado.

## Escopo ainda não homologado em produção

Os testes usaram SQLite. A execução concorrente em PostgreSQL/Railway, o deploy, o site público após a atualização e as chamadas externas com a chave OpenAI de produção ainda precisam ser conferidos na etapa de publicação. O motor externo não foi invocado nesta auditoria; não se afirma que uma resposta paga tenha sido validada.

Os resultados locais não demonstram que o site publicado já recebeu as mudanças. Não foi feita migração destrutiva nem recálculo histórico; os novos indicadores e a versão ficam nos snapshots JSON existentes.

## Reprodução

Na pasta backend: ../.venv-validacao/bin/python -m pytest -q. Na pasta frontend: npm run build. Com FastAPI local apontando para banco exclusivo de QA: node tools/homologar_fluxo.mjs. Orientações em tools/README.md. Capturas e saída JSON da execução ficam em tmp/qa; páginas de revisão dos PDFs em tmp/pdfs/qa-item8.
