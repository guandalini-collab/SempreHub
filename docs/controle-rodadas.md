# Controle de rodadas SempreHub

Conceito SempreHub: Professor Guandalini.

## Calendário e permissões

O professor salva uma data por turma e rodada em `PUT /api/professor/turmas/{id}/prazo`. `app/prazos.py` converte 23:59:59 de `America/Sao_Paulo` para UTC usando a base IANA do `zoneinfo`. As duas colunas opcionais da migração 0010 não alteram dados anteriores.

Antes do instante limite, o líder pode salvar rascunhos ou enviar a versão final. A decisão final bloqueia novas escritas. No prazo vencido, as rotas de salvamento e confirmação devolvem HTTP 403; o bloqueio independe do ciclo do agendador.

## Encerramento

1. O calendário detecta prazos vencidos; o professor também pode confirmar **Forçar Fechamento Imediato da Rodada**. Ambos usam o motor existente.
2. O bloqueio transacional da turma serializa salvamento e fechamento. O calendário relê prazo, rodada e status depois de adquirir o bloqueio.
3. No fechamento forçado, rascunhos são preservados e marcados como automáticos. Empresas sem decisão usam a política existente de repetição de escolhas recorrentes, sem repetir investimentos pontuais. Os registros distinguem essa ação de entrega final voluntária.
4. O motor calcula competição, produção, custos, caixa e estoque, grava os resultados e avança o mês na mesma transação. Uma falha reverte o conjunto. O prazo antigo permanece associado ao mês encerrado; não fecha o próximo mês.
5. Após o commit, o fluxo existente prepara relatórios, enviando contexto JSON agregado da concorrência e resultados apurados à OpenAI. Falhas de relatórios não refazem os cálculos nem bloqueiam o novo mês; podem ser repetidas no painel docente.

A OpenAI produz análises narrativas; os valores contábeis continuam sendo apurados pelo motor validado. Mantêm-se rotas, vínculos, parâmetros e resultados históricos. O calendário verifica vencimentos a cada segundo enquanto o serviço está ativo; após reinício, recupera prazos vencidos. A barreira de salvamento vale no instante exato, mesmo antes de o processamento automático terminar.

## Verificações

Testes cobrem UTC equivalente ao horário de Brasília, dias anteriores, segundo anterior, limite exato, turma sem prazo, mês seguinte sem fechamento repetido, rascunho preservado, HTTP 403 e edição novamente disponível na rodada seguinte.
