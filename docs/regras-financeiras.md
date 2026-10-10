# Reconciliação financeira — item 6

Campos legados de caixa e DFC mantêm o saldo operacional assinado. Campos adicionais de balanço disponibilidades, cheque_especial, ativo_total e passivo_total apresentam o déficit no passivo. Cheque não é somado à dívida do motor. Juros projetados no balanço são informativos; a cobrança já existente usa o saldo negativo inicial da próxima rodada.

Curto prazo: vencimento <= rodada + 12. Empréstimos sem vencimento único ou cronograma não são classificados por suposição: liquidez corrente, seca e imediata ficam indisponíveis. Liquidez geral exige títulos com vencimentos registrados. Zero denominador retorna None.

EBIT = lucro líquido + juros na DRE atual, que não possui imposto sobre lucro separado. EBITDA exige depreciação isolada; amortização de ativos, quando registrada, é adicionada. Campos derivados ficam na operação, preservando a DRE de despesas sem duplicar somas.

PMR/PMP usam saldos pendentes originados na rodada atual e faturamento/compras da mesma rodada, multiplicados por 30. Compras de insumos são congeladas separadamente de CMV. Startup sem compras de insumos: PMP indisponível. LTV tradicional: indisponível.

Ponto de equilíbrio operacional tradicional: contribuição = receita menos impostos sobre vendas, CMV, royalties, comissões, frete e refugo. Compromissos de período = demais despesas operacionais registradas, excluídos juros. A classificação didática e os limites são documentados no manual. Margens zero e negativa têm estados específicos; falta de receita ou de estrutura de custos deixa o indicador indisponível.
