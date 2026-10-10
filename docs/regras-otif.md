# OTIF — regras conciliadas do item 4

Cada unidade demandada representa um pedido didático de uma unidade. Não há cadastro de pedidos individuais: a convenção é identificada no resultado, sem alterar tabelas ou históricos.

O denominador é a demanda total, incluindo pedidos não atendidos. Falta de estoque é uma falha de atendimento e não recebe novamente falhas de transporte. Apenas unidades despachadas recebem a taxa da transportadora.

Econômica: 10% de atrasos, 5% de incompletos, com sobreposição de metade dos incompletos; união teórica 12,5%. Padrão: 4%, 2% e sobreposição de 30%; união 5,4%. Premium: 1% de falha geral, sem presumir atraso ou incompletude.

Arredonda-se primeiro a união das falhas de transporte com Decimal e ROUND_HALF_UP (0,5 para cima), limitada aos pedidos despachados. Incompletos e sobreposição são arredondados e limitados à união; atrasos são o saldo conciliado. Em lotes pequenos, as proporções realizadas podem diferir das teóricas. As contagens físicas são sempre inteiras e a identidade atrasos + incompletos − sobreposição + falhas gerais = falhas totais é preservada.

Pedidos perfeitos = pedidos totais − falhas únicas. OTIF = perfeitos / total, armazenado como fração e exibido como percentual. Zero pedidos: Não se aplica. Quinze pedidos econômicos totalmente despachados: duas falhas e treze perfeitos; OTIF 86,67%.

A satisfação usa a mesma proporção realizada de falhas de transporte (incluindo falhas gerais Premium). A ruptura mantém seu efeito separado, sem dupla contagem. Indicadores de transporte não estornam vendas nem movimentam estoque novamente; os efeitos operacionais e contábeis existentes são preservados.
