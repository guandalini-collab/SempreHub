# Validação de preços e datas nas edições de mercado

## Problema encontrado na auditoria de produção

Na turma isolada QA Auditoria Tradicional 10-10-2026 (id 3), a integração real de pesquisa respondeu, mas o rascunho relacionou um custo de R$ 2.200 para um smartphone a uma notícia setorial sem esse preço e atribuiu uma data divergente à análise. A edição permaneceu sem publicação. Turmas anteriores e resultados históricos não foram alterados.

## Correção

Novas pesquisas, revisões e publicações conferem o documento HTTPS citado. Um produto exige `evidencia_custo`, com URL presente em suas fontes e trecho literal que contenha seu nome e um único preço em reais correspondente ao custo informado. Uma URL citada pela busca, sozinha, não comprova um preço. Ausência, alteração do valor, trecho inventado e produto incompatível bloqueiam a operação.

Datas de notícias e análises devem coincidir com a publicação documentada em metadados/JSON-LD da fonte, não com a data da consulta. Produtos sem data publicada podem registrar explicitamente `Consulta em AAAA-MM-DD` com a data da consulta atual. O painel docente permite revisar datas, URL e trecho de comprovação. Nenhum novo campo de estado nem rotina de decisão dos alunos foi renomeado.

Fontes inacessíveis, conteúdo dinâmico sem comprovação disponível ou datas de publicação não documentadas são recusados. É necessário escolher outra fonte verificável; o sistema não inventa evidências para completar a quantidade solicitada. A checagem não certifica automaticamente todas as afirmações narrativas: a revisão do professor continua necessária. Também não transforma preço de aquisição em custo industrial.

A leitura externa aceita apenas HTTPS público, valida endereços e redirecionamentos, fixa o IP na conexão TLS e limita tamanho e tempo das respostas. Conteúdo de scripts não serve como trecho de preço.

Catálogos já publicados permanecem legíveis e não são recalculados. Rascunhos antigos sem evidência precisam de revisão antes de sua primeira publicação. Nenhuma migração ou exclusão de dados é necessária.

## Verificação

- 258 testes do backend passaram, incluindo rejeição de preço inventado, trecho inexistente, produto divergente, data incorreta, ausência de prova, fonte inacessível e endereço privado.
- A regressão cobre pesquisa sem gravação e publicação recusada de rascunho antigo sem prova.
- Compilação TypeScript/Vite concluída.
- Os 18 submenus do professor foram conferidos em produção, com um único painel ativo por clique.
- A integração real respondeu na turma QA; a auditoria de evidência identificou a falha que motivou esta correção.

A auditoria geral ainda inclui testes de fechamento concorrente no PostgreSQL e fluxos autenticados dos alunos em produção; não devem ser considerados concluídos apenas com estes resultados.
