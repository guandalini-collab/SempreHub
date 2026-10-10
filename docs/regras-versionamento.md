# Versionamento e compatibilidade — item 7

Novos resultados avançados Tradicional e Startup persistem engine_version=2.0.0-deterministic-indicators no JSON de detalhes. A coluna inteira versao_motor da turma e o campo legado do snapshot permanecem compatíveis com a seleção de arquitetura existente.

Resultados sem tag são identificados como 1.0.0-legacy somente na cópia de leitura da API, relatório e CSV. Não há UPDATE de resultados antigos nem migração destrutiva. Ausência de indicadores não é convertida em zero nem em Não se aplica; campos ausentes permanecem indisponíveis. Não são necessárias novas colunas para indicadores já armazenados em JSON.

Ao preparar a primeira nova rodada de estado sem a tag atual, a cópia de trabalho recebe risco 0, performance 1, defeito .02 e sequência de horas extras 0. Máquinas preservam custo, valor líquido, vida útil e ativação; apenas risco/condição operacionais começam limpos. O estado inicial histórico é congelado antes dessa inicialização. Após a primeira rodada, a tag persiste e os indicadores acumulam normalmente. Não se reiniciam a cada mês.

O painel docente e CSV mostram a versão por rodada. A tag informa a origem do resultado, sem recalculá-lo ou trocar os pesos e métricas de avaliação. DRE, patrimônio e capital aportado seguem as bases registradas. Empréstimos/aportes não se tornam receitas; reclassificação de cheque especial não altera patrimônio nem gera segunda despesa.
