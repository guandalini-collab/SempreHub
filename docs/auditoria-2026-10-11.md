# Auditoria funcional do SempreHub — 11 de outubro de 2026

## Resultado e escopo

Auditoria da versão publicada 91814a8 e validação das duas correções de interface descritas abaixo. Os testes ativos em produção usaram somente as turmas QA Auditoria Tradicional 10-10-2026 (id 3, empresa 2) e QA Auditoria Startup 11-10-2026 (id 4, empresa 3), com alunos fictícios. Ambas ficaram ocultas para ingresso. Turmas anteriores, modelos e históricos existentes não foram alterados.

## Verificações locais concluídas

- Backend: 258 testes aprovados; cinco avisos preexistentes de descontinuação, sem falhas.
- Frontend: TypeScript e Vite compilados após as correções.
- Homologação pelo navegador contra FastAPI e SQLite exclusivo de QA: duas rodadas por modelo, líder e integrante, rascunhos, confirmação final, investimentos opcionais zero, cenários extremos, histórico imutável, menus e downloads. Reexecutada após as duas correções: aprovada.
- Prazos: testes de um microssegundo antes, no limite e depois de 23:59:59 de Brasília; sem bloqueio diário; próximo mês liberado. Fechamento automático e manual concorrentes: um resultado e um avanço no banco local.

## Verificações no site e PostgreSQL de produção

- Perfil professor: 18 submenus isolados; três manuais presentes. Nenhum painel anterior permaneceu visível ao trocar o submenu.
- Perfil aluno: 38 submenus conferidos em cada modelo; um painel visível por item.
- Integrante não pode gravar decisões: HTTP 403. Líder envia decisão incompleta: HTTP 422 com as pendências.
- Líder salva rascunho pela tela, recarrega e mantém preço R$ 123,01. Integrante vê o mesmo preço com controle desabilitado.
- Confirmação final pelo modal original: envio aceito; banner de modo leitura e controles desabilitados, com valores preservados.
- API aceita decisões completas com marketing, P&D e crédito em zero. Depois do envio final, tentativa de alteração pelo líder retorna HTTP 403.
- Dois acionamentos manuais em paralelo por duas abas: turma tradicional avançou de 1 para 2 e gerou somente um resultado da rodada 1. Isso confirma a serialização do caminho manual no PostgreSQL; não equivale a observar a corrida entre cronômetro e botão em produção.
- Segunda rodada tradicional: produção zero, todos os funcionários desligados e marketing de R$ 100.000. Caixa final -R$ 93.485,08; disponibilidades zero; cheque especial positivo de R$ 93.485,08. Ativo menos passivo igual ao patrimônio. OEE/eNPS nulos, sem zeros artificiais.
- Snapshot completo da rodada 1 permaneceu idêntico depois da rodada 2.
- Startup: decisão com funcionários, salário acima da referência, benefícios e treinamento processada sem exigir máquinas ou estoque industrial; eNPS 100, OEE nulo e versão 2.0.0-deterministic-indicators. Uma rodada executada em produção; duas no ambiente local.
- Manuais: HTTP 401 sem autenticação para aluno, professor e mídias; aluno recebe HTTP 200 para aluno/mídias e HTTP 403 para professor. Abertura pública não exibe manuais.
- Mercado: rascunho antigo com custo não comprovado permaneceu aguardando revisão. Tentativa de liberar pela tela foi bloqueada com mensagem explícita; não foi publicado aos alunos.

## Problemas encontrados e corrigidos

1. O atalho do Manual rápido na página inicial autenticada apontava diretamente para /manuais/ e não enviava o token. Passou a usar LinkManual, o mesmo componente autenticado do menu lateral, para os dois perfis.
2. Sem catálogo publicado, o painel de produtos permanecia em “Carregando catálogo de produtos…”. Agora distingue consulta concluída sem edição e informa que o professor ainda não disponibilizou catálogo. Não altera a obrigação de revisar nem inventa produtos/preços.

## Limites da evidência e verificações ainda não concluídas

- Não foi aguardado o horário real de 23:59:59 em produção. O limite e a concorrência automático/manual passaram em testes locais; a concorrência manual/manual foi observada em produção. Não se afirma ter observado o disparo do calendário no Railway nesta execução.
- A nova pesquisa paga, solicitando somente um produto, foi rejeitada em produção: “O trecho de custo não foi encontrado na fonte ou não identifica o mesmo produto”. A edição inválida não foi persistida. Ainda não há nesta auditoria uma nova edição com evidências válidas gerada pela API externa, publicada e utilizada por alunos. A proteção funciona, mas a obtenção de catálogo válido pela pesquisa externa permanece uma pendência funcional; o teste negativo não demonstra sucesso desse fluxo positivo completo.
- O navegador conectado não entregou evento de download docente durante o prazo do instrumento. Downloads funcionaram na homologação local; permissões e entrega de PDFs foram comprovadas via API de produção. A gravação do arquivo pelo Chrome conectado não foi confirmada.
- Não houve teste de carga, recuperação de backup ou falha de infraestrutura. Os resultados não garantem disponibilidade futura de serviços externos.

Credenciais de QA e arquivos temporários ficam em tmp/qa, ignorados pelo Git; não constam neste relatório. As evidências de interface e o roteiro automatizado estão nessa pasta e em tools/homologar_fluxo.mjs.
