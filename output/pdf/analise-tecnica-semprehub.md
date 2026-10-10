# SempreHub
# Análise técnica e pedagógica
Relatório para revisão em outro chat
Data de referência: 10 de outubro de 2026
Projeto, conceito e marca: Professor Guandalini

## Objetivo e conclusão principal
Este relatório reúne o contexto do SempreHub, as regras propostas, a situação da implementação e os pontos que precisam ser resolvidos antes da publicação. Permite revisar o sistema sem depender da conversa anterior.
As regras propostas são viáveis, mas precisam ser integradas ao motor existente com cuidado. Há conflitos entre cálculos anteriores e regras novas, definições abertas e alterações locais ainda não publicadas porque a validação não terminou.
Este é um retrato da auditoria relatada em 10 de outubro de 2026. A geração deste PDF não representa uma nova auditoria da produção nem a publicação das alterações pendentes.

## 1. O que é o SempreHub
O SempreHub é um simulador educacional de negócios criado conceitualmente pelo Professor Guandalini. Destina-se a estudantes de Ensino Médio e Superior, inclusive iniciantes em administração e alunos de diferentes áreas.
A proposta é formar equipes, administrar uma empresa simulada, interpretar informações de mercado e resultados, discutir alternativas, tomar decisões integradas entre departamentos e aprender com suas consequências nas rodadas seguintes.
A aplicação está hospedada no Railway, tem código no GitHub e está disponível em www.semprehub.com.br. A arquitetura observada utiliza React e TypeScript no frontend, Python/FastAPI no backend, banco relacional em produção, motores de simulação e integração com OpenAI para funcionalidades existentes.
A integração com OpenAI não exige que resultados numéricos sejam escolhidos livremente por um modelo. As novas regras de OEE, OTIF e eNPS devem ser determinísticas.
### Modos e cenários a preservar
Existem modelo básico (identificado internamente como legado), empresa tradicional e Startup, além dos cenários de abertura de negócio e recuperação de empresa em crise.
Uma regra de negócio dizendo que a empresa será sempre tradicional e começará sempre zerada restringiria funcionalidades existentes. A nova especificação deve ser aplicada ao modo e cenário correspondentes, sem eliminar os demais.

## 2. Requisitos já estabelecidos pelo professor
### Turmas, equipes e liderança
O professor cria a turma com nome livre. O aluno ingressa na turma disponibilizada pelo professor e encontra colegas e equipes para participar. A formação deve respeitar as regras do sistema. Um integrante assume a liderança e envia as decisões; os demais acompanham e contribuem. A transferência de liderança respeita a mudança para a próxima rodada. Decisões finais incompletas devem ser bloqueadas com indicação da pendência.
### Decisões empresariais
Conforme o modelo, a equipe pode comprar máquinas, aumentar produção, contratar e demitir, utilizar horas extras, investir em treinamento, manutenção, benefícios e P&D, definir preços e campanhas, escolher logística, solicitar crédito e administrar pagamentos e recebimentos.
Essas escolhas são opcionais. A ausência de investimento não deve travar arbitrariamente o jogo, mas pode gerar consequências proporcionais às condições da empresa.
### Interface e manuais
A navegação deve usar menu lateral, submenus e conteúdo à direita, com resultados separados para evitar uma tela longa e poluída. Deve manter modo de leitura após envio final e indicação clara das decisões pendentes.
O pedido de um grande dashboard em bloco de texto conflita com essa organização. Significados, fórmulas, exemplos e orientações de interpretação devem estar no manual. A tela mostra valores e contexto necessário, encaminhando a equipe ao manual para fundamentar suas decisões.

## 3. Situação real de publicação e implementação
### Versão pública confirmada antes deste trabalho
A última publicação confirmada moveu os atalhos da rodada do aluno para o submenu lateral. Commit: 74320655d04027cf09f63e0770f1801a12a0f01f. O Railway confirmou sucesso e a versão correspondente foi verificada no site.
### Alterações locais não publicadas
O trabalho atual inclui módulo de indicadores determinísticos no backend, integração parcial aos motores tradicional e Startup, mudança da taxa de refugo, resultados do aluno por submenus, catálogo dos 33 indicadores e atualização do manual do aluno.
Essas alterações são locais e não devem ser tratadas como disponíveis em produção.
### Validação e limites
A compilação do frontend passou. A última suíte completa do backend apresentou 136 testes aprovados e cinco falhas. As falhas envolvem expectativas anteriores de estoque final, produtos aproveitáveis, refugo, produção efetiva, lucro e custo dos produtos vendidos.
Parte das diferenças decorre das novas regras, como defeitos iniciais de 2%. Isso não autoriza mudar expectativas apenas para fazer testes passarem. É necessário conferir conservação de estoque, custos, caixa e patrimônio.
As equipes de teste não foram zeradas. A publicação das novas regras, os testes específicos dos indicadores e a revisão visual final do manual atualizado não foram concluídos. O último prompt ampliado não foi incorporado integralmente.

## 4. Regra fundamental de integração
O indicador deve refletir os registros do motor, com coerência nos demonstrativos. Se manutenção insuficiente reduz a produção aproveitável, isso pode reduzir vendas ou estoque disponível. Faturamento, CMV, refugo, caixa e patrimônio precisam acompanhar o efeito.
Não basta exibir OEE menor se a empresa continua operando como antes. Também não se pode reduzir produção por defeitos e descontar novamente a mesma perda do faturamento sem considerar estoque e vendas efetivas.
A sequência precisa distinguir: capacidade disponível; produção realizada; produção aproveitável; estoque disponível; demanda e pedidos; vendas e entregas; receita e custos; recebimentos e pagamentos; resultado e posição financeira.

## 5. Auditoria do OEE
### Regras aprovadas
OEE = Disponibilidade x Performance x Qualidade. Condição inicial: disponibilidade de 100%, performance de 100%, qualidade de 98% e OEE inicial teórico de 98%.
Manutenção de R$ 1.000 ou mais zera o risco de quebra. Investimento menor aumenta o risco proporcionalmente à insuficiência. Sem manutenção, o risco cresce cumulativamente cinco pontos percentuais por rodada.
Cada R$ 100 de treinamento por funcionário de produção aumenta performance em dois pontos percentuais e reduz defeitos em 0,5 ponto percentual. Performance tem teto de 100%; defeitos têm piso de 0,5%. Sem treinamento, performance cai 0,5 ponto percentual por rodada.
Sem máquinas operando ou com produção planejada zero: Não se aplica.
### Exemplo matemático
Primeira rodada com máquina ativa, sem manutenção e sem treinamento: disponibilidade 95%, performance 99,5%, qualidade 98%. OEE = 0,95 x 0,995 x 0,98 = 0,926345, ou 92,6345% (92,63% com duas casas). Isso distingue o estado inicial teórico da consequência das decisões da primeira rodada.
### Decisões necessárias
O risco provisório é agregado à empresa. Uma máquina nova pode compartilhar penalização das antigas. É preciso escolher entre risco da operação como um todo e controle por equipamento com consolidação posterior.
O motor anterior já usa condição das máquinas e manutenção proporcional ao custo. O alvo fixo novo pode duplicar efeitos. Ambas as regras precisam ser harmonizadas.
Há fluxos que admitem produção até 130% da capacidade calculada. É preciso distinguir horas extras, sobrecarga, capacidade emergencial e performance limitada a 100%.
Não foi demonstrada separação entre funcionários de produção, administrativos e comerciais. O cálculo provisório usa o total de funcionários no treinamento por pessoa; isso precisa ser documentado ou ajustado.
Qualidade esperada e observada diferem em lotes pequenos. Dois por cento de defeito em dez peças equivale a 0,2 peça; o arredondamento pode produzir qualidade observada de 100%, sem alterar a taxa esperada de 98% do modelo.

## 6. Auditoria do OTIF
### Regras aprovadas
OTIF = Pedidos perfeitos / Pedidos totais x 100. O pedido perfeito deve atender simultaneamente prazo, quantidade e especificações. Atraso e incompletude no mesmo pedido contam como uma única falha.
Econômica: 10% de atrasos, 5% de incompletos e metade dos incompletos também atrasados. Padrão: 4% de atrasos, 2% de incompletos e 30% dos incompletos também atrasados. Premium: 1% de falha geral, sem detalhamento de tipo ou sobreposição.
Sem falta de estoque, os percentuais esperados são: Econômica, 10% + 5% - 2,5% = 12,5% de falhas únicas e OTIF de 87,5%; Padrão, 4% + 2% - 0,6% = 5,4% de falhas e OTIF de 94,6%; Premium, OTIF de 99% se não houver outras falhas consideradas.
### Decisões necessárias
Demanda, cliente, pedido e unidade não são equivalentes. Um cliente pode fazer vários pedidos e cada pedido conter vários produtos, unidades e entregas parciais. A implementação provisória trata uma unidade de demanda como pedido didático: documentar essa simplificação ou substituí-la por registros de pedidos.
Percentuais produzem frações em volumes pequenos. Escolher indicadores esperados com quantidades equivalentes ou pedidos inteiros com distribuição determinística. Não apresentar 0,3 entrega como ocorrência física.
O material usou total de pedidos e total de pedidos entregues como denominador. Fixar uma definição e o tratamento dos não entregues.
Falta de estoque pode causar incompletude, mas demanda potencial perdida não é automaticamente um pedido confirmado ou uma entrega incompleta.
OEE baixo pode reduzir produtos disponíveis; não deve reduzir OTIF diretamente por multiplicação. O efeito deve passar por estoque e atendimento.
A implementação provisória trata a falha premium como atraso. Essa é interpretação adicional, não regra expressa do professor. Sem pedidos: Não se aplica.

## 7. Auditoria do eNPS
### Regras aprovadas
Cada funcionário começa com nota 7. Salário acima da referência: +1; abaixo: -2; benefícios: +1; horas extras recorrentes: -1. Notas finais limitadas de 0 a 10. Promotores: 9 e 10; neutros: 7 e 8; detratores: 0 a 6.
eNPS = percentual de promotores - percentual de detratores. Escala de -100 a +100 pontos. Sem funcionários: Não se aplica.
### Decisões necessárias
Com condições iguais, todos recebem notas iguais; o indicador tende a -100, 0 ou +100. É fiel ao prompt, mas reduz variedade pedagógica. Distribuição distinta exige regras explícitas para grupos, sem diferenças aleatórias inventadas.
Qualquer benefício positivo concede um ponto: R$ 1 e R$ 500 podem ter o mesmo efeito, com custos distintos. Confirmar se isso é intencional ou definir faixas.
Qualquer salário acima da referência recebe o mesmo bônus. Definir se a referência é fixa, configurada pelo professor, variável por rodada ou por função.
Duas rodadas consecutivas foi a interpretação provisória de horas extras recorrentes. Definir mínimo de horas, duração da penalização e tratamento de recém-contratados.
A nota provisória é recalculada a partir de 7 com condições atuais, não acumulada indefinidamente. Isso precisa ser assumido explicitamente.
O eNPS é pesquisa simulada por regras didáticas, não pesquisa real. Não confundir com o indicador de moral já existente.

## 8. Auditoria de marketing e vendas
O novo prompt propõe leads = anúncios / R$ 5; conversão de 10%; bônus de desconto e penalização de preço alto; novos clientes = leads x conversão; CAC = anúncios / novos clientes; ticket = faturamento / novos clientes.
Substituir toda a demanda por essa fórmula pode permitir comprar clientes independentemente de concorrentes, portfólio, qualidade, marca, canais e capacidade. A solução mais coerente é integrar o funil ao mercado competitivo, não substituí-lo.
Definir: custo por lead por canal; despesas incluídas no orçamento; limite de preço muito acima da média; referência do desconto; efeito do desconto sobre receita; recompra; clientes orgânicos; piso e teto da conversão; arredondamento dos clientes; restrições de estoque e capacidade.
Um aumento de 10% para 11% é um ponto percentual. Aumentar 10% em 1% relativo gera 10,1%. A regra deve declarar qual usa.
CAC precisa identificar os gastos incluídos. O LTV existente de Startup usa margem por cliente e churn, não receita acumulada. As duas bases precisam ser diferenciadas.

## 9. Auditoria financeira e contábil
Liquidez exige classificar caixa, receber de curto prazo, estoques, direitos de longo prazo, pagar de curto prazo, dívida de curto e longo prazo e cheque especial. Não basta dividir ativos totais por dívidas totais.
Caixa negativo deve ser tratado coerentemente: distinguir dinheiro disponível, financiamento e cheque especial. Não usar saldo negativo como disponibilidade positiva.
Liquidez abaixo de 1 sinaliza atenção, mas não comprova insolvência sem examinar vencimentos e realizabilidade dos ativos.
Margem bruta precisa declarar receita bruta ou líquida de tributos sobre vendas. A implementação provisória usa receita líquida; documentar a convenção.
EBITDA não permite adicionar indiscriminadamente impostos sobre vendas, principal de empréstimos ou todos os desembolsos financeiros. Amortização contábil de ativos e amortização de dívida são distintas.
PMR e PMP com 365 dias exigem dados anuais. Rodadas mensais precisam de saldos, receita ou compras e dias coerentes. Compras não equivalem ao CMV.
Quebras, atrasos e devoluções não aumentam automaticamente contas a pagar. Cada efeito deve gerar transação definida: redução de vendas, devolução, despesa, perda de estoque, obrigação ou pagamento efetivo.

## 10. NPS, atendimento e churn
NPS base de 80% mistura conceitos: satisfação pode usar escala 0 a 100; NPS é promotores menos detratores, de -100 a +100 pontos. NPS verdadeiro exige respostas simuladas e classificação de clientes.
Faltam decisões ou registros de chamados de SAC, respostas, qualidade do atendimento, investimento em pós-venda, clientes ativos, perdas e recompras.
Churn exige população inicial, evento de perda, taxa base, momento de aplicação, recuperação e limite máximo. Não se pode perder mais clientes do que existem.
No tradicional, uma compra não cria automaticamente contrato recorrente. O churn precisa ter significado compatível com o negócio. Definir se perdas são cumulativas e distinguir percentuais de pontos percentuais.

## 11. Compras e suprimentos
A proposta acrescenta quatro dias úteis a fornecedores baratos ou não homologados. Isso exige fornecedores com características, prazo base, pedidos de compra, datas, calendário, estoque em trânsito e momento em que insumos se tornam utilizáveis.
Exibir mais quatro dias sem atrasar materiais seria apenas visual. Fornecedor barato não deve ser universalmente classificado como inferior; esse comportamento deve ser parâmetro didático de categoria específica.

## 12. Os 33 indicadores solicitados
Liquidez: corrente, seca, imediata e geral.
Marketing: ROI, CAC, LTV, LTV/CAC e conversão.
Finanças: margem bruta, margem líquida, EBITDA, ponto de equilíbrio, PMR e PMP.
RH: turnover, absenteísmo, receita por funcionário, ROI de treinamento, custo por contratação e eNPS.
Produção: OEE, produtividade da mão de obra, refugo, utilização da capacidade, lead time e giro de matéria-prima.
Logística: OTIF, ciclo do pedido, custo logístico/faturamento, acuracidade, ocupação do armazém e última milha.
Incluir um indicador no manual não significa que ele esteja calculado no sistema. Absenteísmo exige horas previstas e ausentes; ROI de treinamento exige ganho atribuível; contratação exige custos de recrutamento; produtividade exige horas; lead time exige início e fim; acuracidade exige contagem física simulada; ocupação exige capacidade e volume; última milha exige custo específico; ROI de marketing exige atribuição de receita; conversão exige base compatível de leads e compradores.
A interface deve diferenciar valor calculado, estimativa do modelo, dado indisponível e não aplicável. Nenhum desses estados equivale automaticamente a zero.

## 13. Histórico e equipes abertas
As equipes atuais foram identificadas pelo professor como testes. Isso permite validar mudanças sem tratar seus resultados como avaliações definitivas, mas não autoriza apagamento automático.
Rodadas antigas devem permanecer como calculadas. Não reescrever silenciosamente lucro, estoque, caixa, indicadores ou notas.
Empresas existentes podem não ter os campos novos. Inicializar valores definidos, com compatibilidade e sem erros de leitura.
É recomendável registrar versão das regras em cada resultado, distinguindo motor antigo, novos indicadores e revisões futuras. Isso ajuda a explicar diferenças entre testes.

## 14. Avaliação automática do professor
Revisar se novos indicadores entram na nota, pesos, modelos aplicáveis, não aplicabilidade, dados ausentes e dupla penalização.
Se refugo já reduz lucro e lucro compõe a nota, penalizar refugo novamente aumenta o peso da mesma consequência. Pode ser intencional, mas deve ser explícito.
Não penalizar ausência de OEE numa empresa sem máquinas quando equipamentos são opcionais ou não se aplicam ao modelo.

## 15. OpenAI e motor determinístico
Preservar a integração existente. Separar motor numérico e camada de narrativa.
O motor aplica fórmulas, atualiza estados, calcula produção, vendas, custos e indicadores, reconcilia demonstrativos e produz resultados reproduzíveis.
A narrativa explica resultados, relaciona causas e consequências e usa dados do sistema, sem substituir cálculos por números inventados.
O feedback pedagógico não decide sozinho que uma equipe foi melhor: interpreta resultados já calculados.

## 16. Validações antes de publicar
### Matemática
Validar OEE inicial, risco acumulado, manutenção parcial e integral, teto de performance, piso de defeitos e condições de não aplicação. Validar OTIF com sobreposição, ausência de pedidos, estoque insuficiente e falha única. Validar eNPS sem funcionários, categorias de nota, recorrência de horas extras e reprodutibilidade.
### Contabilidade
Conferir estoque inicial + entradas - saídas = final; refugo uma única vez; CMV dos produtos vendidos; caixa inicial + variação = final; reconciliação de fluxos operacionais, investimento e financiamento; balanço equilibrado; patrimônio compatível com resultado; compras diferentes de CMV; máquinas diferentes de despesa integral do mês.
### Integração
Conferir rascunho, envio final, bloqueio após envio, fechamento manual e automático, próxima rodada, histórico, empresas existentes e acesso do professor.
### Interface e documentação
Conferir submenus, conteúdo à direita, ausência de duplicação, telas menores, não aplicabilidade e indisponibilidade. Conferir capa, marca, sumário, fórmulas, exemplos e correspondência entre manual e regras efetivamente implementadas.

## 17. Decisões para outro chat revisar
1. Preservar ou restringir modos existentes.
2. Definir OEE teórico versus observado.
3. Controlar desgaste por empresa ou máquina.
4. Harmonizar manutenção antiga e nova.
5. Definir pedido, cliente e unidade.
6. Escolher percentuais esperados ou contagens inteiras.
7. Definir falha premium.
8. Confirmar se eNPS homogêneo é suficiente.
9. Definir salário de referência e benefício mínimo.
10. Confirmar horas extras recorrentes.
11. Integrar funil à competição.
12. Definir NPS distinto de satisfação.
13. Criar fornecedores e prazos se o módulo for adotado.
14. Revisar nota automática.
15. Versionar resultados sem reprocessamento silencioso.

## 18. Orientação para o outro chat
Analise esta especificação como revisão de sistema existente. Não presuma que propostas já estejam implementadas ou publicadas. Preserve modos, competição, banco e históricos. Identifique conflitos entre fórmulas, decisões, unidades, prazos e demonstrativos. Diferencie regra aprovada, interpretação adicional e decisão necessária. Mantenha resultados em submenus e explicações no manual. Não proponha números aleatórios nem trate dados ausentes como zero. Avalie a coerência entre indicadores e produção, estoque, vendas, caixa, patrimônio e avaliação pedagógica.
### Situação final
A proposta é viável, mas a implementação local permanece em validação. A versão pública anterior é a última confirmada. As novas regras ainda não estão concluídas nem publicadas.
