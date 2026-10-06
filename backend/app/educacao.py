"""Conteúdo educacional estático usado pelas telas de apoio do SempreHub.

Este módulo mantém o conteúdo didático separado do estado das turmas e das
empresas. As funções devolvem cópias dos dados para que uma tela não possa
alterar o catálogo compartilhado em memória. Valores de mídia são faixas
ilustrativas do material didático e nunca são uma cotação ou uma indicação de
canal para um tipo de empresa.
"""

from copy import deepcopy
from typing import Any


_REFERENCIAS = (
    {
        "id": "porter-1980",
        "autor": "Michael E. Porter",
        "obra": "Competitive Strategy: Techniques for Analyzing Industries and Competitors",
        "ano": 1980,
        "localizacao": "Capítulo 1 — The Structural Analysis of Industries",
        "contribuicao": "As cinco forças para analisar a estrutura e a atratividade de um setor.",
        "nota_edicao": "A numeração pode mudar em traduções e reedições; procure pelo título da seção.",
    },
    {
        "id": "fahey-narayanan-1986",
        "autor": "Liam Fahey e V. K. Narayanan",
        "obra": "Macroenvironmental Analysis for Strategic Management",
        "ano": 1986,
        "localizacao": "Capítulos introdutórios sobre análise do macroambiente e suas dimensões",
        "contribuicao": "Base para observar fatores políticos, econômicos, sociais, tecnológicos, ecológicos e legais.",
        "nota_edicao": "É uma referência de estrutura analítica; a numeração de capítulos deve ser conferida na edição consultada.",
    },
    {
        "id": "kotler-keller-marketing",
        "autor": "Philip Kotler e Kevin Lane Keller",
        "obra": "Administração de Marketing (Marketing Management)",
        "ano": 2012,
        "localizacao": "Capítulos sobre análise de mercado, pesquisa de marketing, segmentação, seleção de mercado-alvo e posicionamento",
        "contribuicao": "Fundamentos para entender clientes, concorrentes, tendências, segmentação e proposta de valor.",
        "nota_edicao": "Os números dos capítulos variam entre edições; use os títulos dos capítulos no índice.",
    },
    {
        "id": "humphrey-swot",
        "autor": "Albert S. Humphrey e equipe do Stanford Research Institute",
        "obra": "Origem histórica da análise SOFT/SWOT no planejamento estratégico",
        "ano": 1960,
        "localizacao": "Relatórios e registros históricos do SRI sobre planejamento corporativo; não há um capítulo único canônico",
        "contribuicao": "Separação entre fatores internos (forças e fraquezas) e externos (oportunidades e ameaças).",
        "nota_edicao": "SWOT é um quadro de síntese, não um diagnóstico automático nem uma nota da empresa.",
    },
    {
        "id": "gitman-financas",
        "autor": "Lawrence J. Gitman e Chad J. Zutter",
        "obra": "Principles of Managerial Finance",
        "ano": 2015,
        "localizacao": "Seções sobre demonstrações financeiras, planejamento financeiro, orçamento de caixa e capital de giro",
        "contribuicao": "Referência para separar lucro, caixa, contas a receber, contas a pagar e necessidade de capital de giro.",
        "nota_edicao": "A numeração varia por edição; procure esses títulos no sumário da edição adotada.",
    },
    {
        "id": "dornelas-empreendedorismo",
        "autor": "José Carlos Assis Dornelas",
        "obra": "Empreendedorismo: Transformando Ideias em Negócios",
        "ano": 2018,
        "localizacao": "Capítulos sobre plano de negócios, mercado, marketing, operação e análise financeira",
        "contribuicao": "Integração entre oportunidade, modelo de negócio, execução e viabilidade.",
        "nota_edicao": "Confira o capítulo equivalente na edição disponível para a turma.",
    },
    {
        "id": "gem-relatorio",
        "autor": "Global Entrepreneurship Monitor (GEM)",
        "obra": "Global Entrepreneurship Monitor — Global Report",
        "ano": 2023,
        "localizacao": "Seções sobre atividade empreendedora, motivações e contexto do ecossistema",
        "contribuicao": "Referência de pesquisa para distinguir motivações e acompanhar indicadores de empreendedorismo.",
        "nota_edicao": "O relatório é atualizado periodicamente; use a edição indicada pelo professor.",
    },
)


def _referencia(ref_id: str) -> dict[str, Any]:
    return {"referencia_id": ref_id}


_ANALISES = (
    {
        "slug": "porter",
        "nome": "As 5 Forças de Porter",
        "titulo_curto": "Análise de concorrência",
        "descricao": "Examina a pressão competitiva e a atratividade estrutural de um setor.",
        "escopo": "microambiente do setor",
        "referencias": [_referencia("porter-1980")],
        "itens": [
            {
                "chave": "rivalidade",
                "nome": "Rivalidade entre concorrentes",
                "pergunta": "Quão intensa é a disputa atual por clientes, preço, qualidade e atenção?",
                "explicacao": "Observe concentração, ritmo de crescimento, diferenciação e custos de mudança. Guerra de preços e campanhas que se repetem podem comprimir margens.",
                "exemplo": "Concorrentes reduzem o preço e ampliam campanhas para disputar a mesma demanda.",
            },
            {
                "chave": "novos-entrantes",
                "nome": "Ameaça de novos entrantes",
                "pergunta": "É fácil que uma nova organização entre e dispute a mesma demanda?",
                "explicacao": "Mapeie capital inicial, tecnologia, marca, acesso a canais, regulação e efeitos de escala como barreiras de entrada.",
                "exemplo": "Uma plataforma de baixo custo e fornecedores acessíveis pode reduzir o investimento necessário para entrar.",
            },
            {
                "chave": "fornecedores",
                "nome": "Poder de barganha dos fornecedores",
                "pergunta": "Quem fornece insumos consegue impor preço, prazo, qualidade ou quantidade mínima?",
                "explicacao": "Considere concentração de fornecedores, existência de substitutos, custo de trocar de parceiro e dependência de um insumo crítico.",
                "exemplo": "Um único fornecedor de matéria-prima essencial alonga prazos e reajusta preços.",
            },
            {
                "chave": "clientes",
                "nome": "Poder de barganha dos clientes",
                "pergunta": "Os compradores podem exigir desconto, prazo, qualidade ou atendimento adicional?",
                "explicacao": "Avalie concentração, sensibilidade ao preço, informação disponível e facilidade de trocar de solução.",
                "exemplo": "Poucos compradores grandes concentram pedidos e conseguem negociar condições melhores.",
            },
            {
                "chave": "substitutos",
                "nome": "Ameaça de produtos substitutos",
                "pergunta": "Que outra solução resolve a mesma necessidade do cliente?",
                "explicacao": "Compare custo, conveniência, desempenho e tendência de adoção de soluções diferentes, mesmo que elas não tenham a mesma tecnologia.",
                "exemplo": "Uma solução digital pode substituir uma compra física quando entrega a mesma utilidade percebida.",
            },
        ],
        "como_usar": "Registre evidências para cada força, estime a pressão como baixa, média ou alta e transforme a análise em hipóteses a testar. A matriz não produz uma decisão automática.",
    },
    {
        "slug": "pestel",
        "nome": "Análise PESTEL",
        "titulo_curto": "Análise de macroambiente",
        "descricao": "Mapeia mudanças externas que podem afetar o setor e que a organização não controla diretamente.",
        "escopo": "macroambiente",
        "referencias": [_referencia("fahey-narayanan-1986")],
        "itens": [
            {"chave": "politico", "nome": "Político", "o_que_avaliar": "Políticas públicas, estabilidade, eleições e prioridades governamentais.", "exemplo": "Mudança em subsídio, compras públicas ou política fiscal."},
            {"chave": "economico", "nome": "Econômico", "o_que_avaliar": "Juros, inflação, desemprego, renda e crescimento.", "exemplo": "Crédito mais caro e perda de poder de compra reduzem a demanda ou a capacidade de investimento."},
            {"chave": "social", "nome": "Social", "o_que_avaliar": "Demografia, comportamento, cultura, valores e hábitos.", "exemplo": "Mudanças na composição etária ou na busca por saudabilidade alteram necessidades."},
            {"chave": "tecnologico", "nome": "Tecnológico", "o_que_avaliar": "Inovação, automação, inteligência artificial, infraestrutura e obsolescência.", "exemplo": "Um novo software diminui o custo de uma operação ou muda a experiência esperada."},
            {"chave": "ecologico", "nome": "Ecológico", "o_que_avaliar": "Sustentabilidade, escassez de recursos, clima e impactos ambientais.", "exemplo": "Evento climático interrompe o fornecimento ou uma regra de reciclagem cria custo de adaptação."},
            {"chave": "legal", "nome": "Legal", "o_que_avaliar": "Legislação trabalhista, proteção de dados, normas setoriais e defesa do consumidor.", "exemplo": "Uma obrigação de privacidade muda a coleta, o armazenamento ou o uso de dados."},
        ],
        "como_usar": "Descreva o sinal observado, o horizonte, a probabilidade estimada, o impacto e a ação de acompanhamento. PESTEL olha o ambiente amplo; Porter olha a arena competitiva. As duas leituras podem alimentar uma SWOT.",
    },
    {
        "slug": "mercado",
        "nome": "Análise de mercado",
        "titulo_curto": "Clientes, concorrência e tendências",
        "descricao": "Organiza evidências sobre quem compra, quem disputa a demanda e como o setor está mudando.",
        "escopo": "mercado e demanda",
        "referencias": [_referencia("kotler-keller-marketing"), _referencia("dornelas-empreendedorismo")],
        "itens": [
            {"chave": "publico", "nome": "Público-alvo", "explicacao": "Descreva quem pode comprar, qual problema quer resolver, como decide e que restrições possui.", "perguntas": ["Quem usa?", "Quem paga?", "O que dispara a compra?", "Que alternativa usa hoje?"]},
            {"chave": "concorrencia", "nome": "Concorrência", "explicacao": "Compare concorrentes diretos e indiretos por proposta de valor, preço, acesso, qualidade e pontos fracos.", "perguntas": ["Que solução substitui a sua?", "Onde há vantagem observável?", "Que promessa não está sendo atendida?"]},
            {"chave": "tendencias", "nome": "Tendências", "explicacao": "Acompanhe mudanças de hábito, tecnologia, renda, regulação e canais, separando evidência de opinião.", "perguntas": ["O que está crescendo?", "O que pode perder relevância?", "Qual fonte sustenta a hipótese?"]},
        ],
        "como_usar": "Comece com fontes observáveis, registre data e hipótese e atualize a análise quando novas evidências surgirem. Uma estimativa de mercado não é uma promessa de vendas.",
    },
    {
        "slug": "swot",
        "nome": "Análise SWOT (FOFA)",
        "titulo_curto": "Síntese estratégica",
        "descricao": "Conecta fatores internos da organização a oportunidades e ameaças do ambiente.",
        "escopo": "síntese interna e externa",
        "referencias": [_referencia("humphrey-swot"), _referencia("dornelas-empreendedorismo")],
        "itens": [
            {"chave": "forcas", "nome": "Forças", "tipo": "interno", "explicacao": "Recursos, capacidades ou evidências que favorecem a execução.", "exemplo": "Processo confiável, relacionamento validado ou conhecimento difícil de copiar."},
            {"chave": "fraquezas", "nome": "Fraquezas", "tipo": "interno", "explicacao": "Limitações que reduzem a capacidade de executar ou capturar valor.", "exemplo": "Dependência de uma pessoa, caixa curto ou processo ainda não testado."},
            {"chave": "oportunidades", "nome": "Oportunidades", "tipo": "externo", "explicacao": "Mudanças ou espaços de mercado que podem ser aproveitados.", "exemplo": "Nova necessidade, canal acessível ou alteração tecnológica favorável."},
            {"chave": "ameacas", "nome": "Ameaças", "tipo": "externo", "explicacao": "Riscos do ambiente que podem reduzir demanda, margem ou continuidade.", "exemplo": "Entrada de concorrente, aumento de insumo, regra nova ou crise de fornecimento."},
        ],
        "como_usar": "Escreva itens específicos, baseados em evidências, e converta cada cruzamento relevante em uma ação ou pergunta de validação. SWOT organiza raciocínio; não classifica automaticamente uma empresa.",
    },
    {
        "slug": "financeira",
        "nome": "Análise financeira",
        "titulo_curto": "Viabilidade, indicadores e riscos",
        "descricao": "Usa receitas, custos, lucro, caixa, capital de giro e cenários para avaliar sustentabilidade financeira.",
        "escopo": "desempenho e liquidez",
        "referencias": [_referencia("gitman-financas"), _referencia("dornelas-empreendedorismo")],
        "itens": [
            {"chave": "viabilidade", "nome": "Viabilidade", "explicacao": "Projete receitas, custos, investimentos e retorno esperado; explicite volume, preço e prazo que sustentam a projeção."},
            {"chave": "indicadores", "nome": "Indicadores", "explicacao": "Acompanhe faturamento, margem, lucro, geração de caixa, estoque, contas a receber, contas a pagar e necessidade de capital de giro."},
            {"chave": "riscos", "nome": "Riscos", "explicacao": "Teste queda de vendas, aumento de custos, atraso de recebimentos e necessidade de reserva ou crédito."},
        ],
        "como_usar": "Lucro e caixa respondem a perguntas diferentes: a DRE mede resultado econômico; a DFC acompanha entradas e saídas; o balanço mostra ativos, obrigações e patrimônio em uma data. Não trate aporte ou empréstimo como receita.",
    },
)


_SEGMENTACOES = (
    {
        "slug": "demografica",
        "nome": "Demográfica",
        "o_que_avalia": "Características populacionais mensuráveis.",
        "criterios": ["idade", "gênero", "renda mensal", "escolaridade", "profissão", "tamanho da família"],
        "exemplo": "Comparar necessidades declaradas por faixas de renda ou composição familiar.",
    },
    {
        "slug": "geografica",
        "nome": "Geográfica",
        "o_que_avalia": "Localização e condições do ambiente em que a pessoa vive ou compra.",
        "criterios": ["país", "estado", "cidade", "bairro", "clima", "densidade urbana ou rural"],
        "exemplo": "Observar diferenças de acesso, logística ou clima entre regiões.",
    },
    {
        "slug": "psicografica",
        "nome": "Psicográfica",
        "o_que_avalia": "Estilo de vida, valores, personalidade e crenças.",
        "criterios": ["valores", "estilo de vida", "personalidade", "interesses", "atitudes"],
        "exemplo": "Investigar se sustentabilidade, status, rotina fitness ou minimalismo influenciam a escolha.",
    },
    {
        "slug": "comportamental",
        "nome": "Comportamental",
        "o_que_avalia": "Como a pessoa se relaciona com a categoria ou com a solução.",
        "criterios": ["frequência de compra", "lealdade", "ocasião de uso", "benefício buscado", "estágio de decisão"],
        "exemplo": "Separar compras recorrentes de compras ocasionais e benefícios de preço de benefícios de qualidade.",
    },
)


def _midia(
    slug: str,
    nome: str,
    categoria: str,
    unidade_venda: str,
    custo_entrada: str,
    pagamento_prazo: str,
    finalidade: str,
    efeito_caixa: str,
    observacao: str | None = None,
) -> dict[str, Any]:
    return {
        "slug": slug,
        "nome": nome,
        "categoria": categoria,
        "unidade_venda": unidade_venda,
        "custo_entrada": custo_entrada,
        "pagamento_prazo": pagamento_prazo,
        "efeito_caixa": efeito_caixa,
        "finalidade": finalidade,
        "observacao": observacao,
    }


_MIDIAS = (
    _midia("meta-ads", "Meta Ads (Instagram/Facebook)", "DIGITAL", "CPM (1.000 impressões) ou CPC (clique)", "R$ 600 a R$ 2.000/mês", "À vista/antecipado: cartão debitado conforme gasto ou PIX/boleto pré-pago.", "Distribuir anúncios segmentáveis e medir impressões, cliques e ações na plataforma.", "Saldo ou cobrança ocorre durante a campanha; reserve caixa antes da veiculação.", "A segmentação disponível, o leilão e a entrega variam; a faixa não é cotação."),
    _midia("google-ads", "Google Ads (busca e sites parceiros)", "DIGITAL", "CPC (clique real) ou formatos da rede", "R$ 900 a R$ 3.000/mês", "Cartão automático pós-pago por limite ou PIX/boleto pré-pago.", "Alcançar pessoas que pesquisam termos e acompanhar cliques, conversões e custo por ação.", "Pode exigir limite ou pré-pagamento antes da entrega.", "Resultados dependem da disputa, qualidade do anúncio e configuração."),
    _midia("youtube-ads", "YouTube Ads", "DIGITAL", "CPV (visualização) ou CPM", "R$ 1.000 a R$ 4.000/mês", "Estrutura de cobrança integrada à carteira de anúncios do Google.", "Exibir vídeo e medir visualizações, alcance e interações.", "Cobrança segue a carteira e o limite configurados.", "Métricas de atenção não equivalem automaticamente a venda."),
    _midia("tiktok-ads", "TikTok Ads", "DIGITAL", "CPM; mínimo didático de campanha de R$ 20/dia", "R$ 1.000 a R$ 2.500/mês", "Cartão ou inserção de saldo em BRL via PIX.", "Distribuir vídeos curtos e acompanhar alcance, visualizações e ações atribuídas.", "Pré-pagamento ou cartão pode bloquear caixa antes da campanha.", "Mínimos e políticas comerciais mudam; confirme na plataforma."),
    _midia("linkedin-ads", "LinkedIn Ads", "DIGITAL", "CPC ou CPM", "R$ 2.500 a R$ 6.000/mês", "Cartão ou linha de faturamento corporativo, quando disponível.", "Exibir campanhas e medir alcance, cliques e geração de contatos na plataforma.", "Linha corporativa pode exigir prazo e limite próprios.", "Acesso a faturamento direto depende de análise do veículo."),
    _midia("midia-programatica", "Mídia programática (banners em portais)", "DIGITAL", "CPM via leilão automatizado", "R$ 3.000 a R$ 10.000/mês", "Pré-pago ou faturado em 15/30 dias por agência ou plataforma DSP.", "Comprar impressões em inventário de portais por leilão e acompanhar alcance e cliques.", "O faturamento pode deslocar a saída de caixa para depois da veiculação.", "Inventário, segurança de marca e medição exigem conferência contratual."),
    _midia("pinterest-ads", "Pinterest Ads", "DIGITAL", "CPM ou CPC", "R$ 600 a R$ 1.500/mês", "Cartão cadastrado ou boleto, conforme plataforma.", "Exibir imagens e vídeos e medir alcance, cliques e ações.", "Antecipação ou limite de cartão pode ser necessário.", "Custos variam pelo leilão e pela configuração."),
    _midia("disparos-oficiais", "Disparos automáticos (WhatsApp/SMS/Push)", "DIGITAL", "Custo por mensagem entregue via API oficial", "R$ 300 a R$ 1.500/mês", "Pré-pago ou mensalidade; créditos de mensagens são comprados antecipadamente.", "Enviar mensagens transacionais ou de relacionamento com consentimento e medir entrega e interação.", "Créditos pré-pagos saem do caixa antes do uso.", "A operação deve observar consentimento, políticas da plataforma e proteção de dados."),
    _midia("tv-aberta", "TV aberta", "TRADICIONAL", "Inserção de 30 segundos por programa/audiência", "R$ 5.000 a R$ 20.000+/mês", "Faturado após veiculação, com prazo didático de 15 a 21 dias.", "Alcançar audiência por inserções audiovisuais e acompanhar alcance estimado e comprovação de veiculação.", "Pagamento posterior pode casar campanha com recebimentos, conforme contrato.", "Preço depende de praça, programa, audiência e negociação."),
    _midia("tv-assinatura", "TV por assinatura", "TRADICIONAL", "Inserção de 30 segundos por pacote/região", "R$ 2.500 a R$ 8.000/mês", "Boleto faturado após o período de exibição.", "Veicular vídeo em pacotes ou regiões e acompanhar alcance estimado.", "A saída de caixa costuma ocorrer depois da exibição, conforme prazo.", "Pacotes e disponibilidade são comerciais e variáveis."),
    _midia("radio-local", "Rádio local", "TRADICIONAL", "Spot de 30 segundos; pacotes de 60 a 90 inserções", "R$ 1.500 a R$ 4.500/mês", "Boleto para cerca de 30 dias após o fim do mês, mediante comprovação.", "Repetir mensagem em áudio e acompanhar inserções contratadas e cobertura estimada.", "Veiculação pode anteceder o pagamento faturado.", "Praça, horário e pacote alteram a negociação."),
    _midia("jornal-impresso", "Jornais impressos", "TRADICIONAL", "Centímetro por coluna ou fração de página", "R$ 800 a R$ 3.500/edição", "Boleto à vista ou faturado; prazo didático de até 28 dias.", "Publicar anúncio em edição impressa e registrar circulação e inserção contratada.", "Pode permitir pagamento posterior, segundo o veículo.", "Circulação e formato devem ser confirmados com o veículo."),
    _midia("revista-segmentada", "Revistas", "TRADICIONAL", "Página, dupla ou encarte; edição mensal/bimestral", "R$ 1.500 a R$ 6.000/edição", "Antecipado ou parcelado no fechamento do arquivo técnico.", "Construir presença editorial e registrar edição, formato e circulação declarada.", "O pagamento pode anteceder a impressão.", "Publicação e prazo dependem do fechamento da edição."),
    _midia("outdoor", "Outdoor tradicional", "OOH", "Bi-semana de 14 dias por ponto", "R$ 1.200 a R$ 4.000/ponto", "Boleto pós-pago em 15 ou 30 dias a partir da colagem.", "Exibir mensagem em ponto físico durante período contratado e acompanhar período de exposição.", "Campanha pode rodar antes do pagamento faturado.", "Disponibilidade, praça e produção da peça devem ser orçadas separadamente."),
    _midia("painel-led", "Painel de LED de rua", "OOH", "Cota mensal; inserções rotativas de 10 segundos", "R$ 1.500 a R$ 6.000/mês", "Boleto mensal durante a vigência.", "Exibir peças audiovisuais rotativas e acompanhar cota, horários e comprovação.", "Pagamento mensal pode ocorrer durante a vigência do contrato.", "Frequência real depende da grade e do contrato."),
    _midia("busdoor", "Busdoor/Backbus", "OOH", "Mensalidade por veículo", "R$ 600 a R$ 1.500/mês", "Boleto mensal; contratos didáticos mínimos de 3 a 6 meses.", "Expor mensagem na traseira ou vidro de ônibus e acompanhar veículos e período.", "Compromisso mínimo exige projetar caixa de vários meses.", "Rotas, autorização e produção alteram o custo."),
    _midia("mobiliario-urbano", "Mobiliário urbano", "OOH", "Bi-semana ou cota mensal por ponto", "R$ 2.000 a R$ 7.000/ponto", "Boleto pós-exibição ou mensal, conforme exibidora.", "Exibir comunicação em abrigos, relógios e painéis iluminados e registrar pontos contratados.", "Pode haver prazo após a exibição; confirme vencimento.", "Localização, autorização e produção são componentes separados."),
    _midia("telas-elevador", "Telas de elevador/corporativas", "OOH", "Cota mensal de inserções em circuito", "R$ 1.500 a R$ 3.500/circuito", "Mensalidade faturada via boleto contra o CNPJ.", "Repetir mensagens em circuito interno e acompanhar prédios, telas e vigência.", "Saída de caixa mensal durante o contrato.", "A cobertura é limitada ao circuito contratado."),
    _midia("streaming-audio", "Streaming de áudio", "AUDIO_ENTRETENIMENTO", "CPM de áudio com banner clicável", "R$ 1.000 a R$ 3.000/mês", "Cartão automático na plataforma self-service.", "Inserir áudio e medir alcance, reprodução e interação do banner.", "Cobrança costuma ocorrer na plataforma durante a campanha.", "Entrega e métricas seguem configuração e inventário."),
    _midia("podcast", "Podcast (patrocínio)", "AUDIO_ENTRETENIMENTO", "Testemunhal ou spot por episódio", "R$ 500 a R$ 10.000/episódio", "À vista ou 50/50; sinal no fechamento e saldo na publicação.", "Associar mensagem a episódio e registrar entregáveis e data de publicação.", "Pode exigir sinal antes e saldo próximo da publicação.", "Formato, audiência declarada e direitos de uso devem constar do contrato."),
    _midia("cinema", "Canais de cinema", "AUDIO_ENTRETENIMENTO", "Cota mensal por sala; vídeo antes da sessão", "R$ 1.200 a R$ 3.500/sala", "Boleto mensal faturado pela distribuidora comercial.", "Exibir vídeo antes de sessões e acompanhar salas, período e comprovação.", "Pagamento mensal pode suceder a exibição.", "Praça, sessão e disponibilidade mudam o custo."),
    _midia("influencia", "Marketing de influência", "INFLUENCIA_MATERIAIS", "Pacote de entregáveis (Reels, Stories etc.)", "R$ 300 a R$ 5.000+ por ação", "Normalmente 50% de sinal via PIX e 50% pós-entrega.", "Produzir conteúdo com entregáveis acordados e acompanhar publicação e métricas declaradas.", "Sinal reduz caixa antes da entrega; saldo ocorre depois.", "Contrate identificação publicitária, direitos de uso e comprovação de entrega."),
    _midia("panfletagem", "Panfletagem estruturada", "INFLUENCIA_MATERIAIS", "Milheiro impresso mais diárias de promotores", "R$ 400 a R$ 800/ação", "Gráfica à vista; promotores pagos ao fim da diária.", "Distribuir material físico em locais e períodos definidos e registrar quantidade e execução.", "Impressão exige adiantamento; mão de obra sai no dia da ação.", "Permissões locais, segurança e descarte precisam ser considerados."),
    _midia("materiais-pdv", "Materiais de PDV", "INFLUENCIA_MATERIAIS", "Peça ou lote de wobblers, totens e móbiles", "R$ 200 a R$ 2.000/lote", "À vista ou parcelado; cartão em até 3 vezes ou PIX faturado quando aceito.", "Apoiar comunicação no ponto de venda com materiais físicos e controlar lote entregue.", "Pode haver pagamento imediato ou parcelas conforme fornecedor.", "Produção, instalação e reposição podem ter custos distintos."),
)


_CATEGORIAS_MIDIA = (
    {"slug": "DIGITAL", "nome": "Mídias digitais", "descricao": "Canais em plataformas e internet, com cobrança por impressão, clique, visualização, mensagem ou carteira."},
    {"slug": "TRADICIONAL", "nome": "Mídias tradicionais e imprensa", "descricao": "Televisão, rádio, jornais e revistas com inserções, pacotes ou edições."},
    {"slug": "OOH", "nome": "Mídia exterior (OOH)", "descricao": "Comunicação em pontos físicos, circuitos, mobiliário urbano e veículos."},
    {"slug": "AUDIO_ENTRETENIMENTO", "nome": "Áudio e entretenimento", "descricao": "Streaming de áudio, podcasts e exibição em salas de cinema."},
    {"slug": "INFLUENCIA_MATERIAIS", "nome": "Ativações, materiais e influência", "descricao": "Entregáveis de influência, distribuição física e materiais no ponto de venda."},
)


_CAVEATS = {
    "precos": "As faixas são referências didáticas fornecidas para o exercício. Não são cotação, promessa de alcance nem recomendação; confirme praça, período, produção, tributos e condições com o veículo.",
    "iof": "Use 3,5% de IOF apenas como hipótese configurável do exercício quando houver operação internacional e fechamento de câmbio. A incidência e a alíquota dependem da operação, do meio de pagamento e da legislação vigente.",
    "retencoes": "Publicidade tradicional pode envolver retenções na fonte e obrigações documentais conforme serviço, fornecedor e regime. O simulador não substitui orientação contábil ou fiscal.",
    "caixa": "Mídias digitais frequentemente exigem cartão, saldo ou pré-pagamento; mídias tradicionais e OOH podem faturar após a veiculação. O prazo é contratual e deve entrar na DFC como premissa, separado do reconhecimento da despesa.",
    "protecao_dados": "Disparos e segmentação devem observar consentimento, finalidade, segurança e a legislação de proteção de dados aplicável.",
    "neutralidade": "O catálogo descreve a finalidade de cada meio e seus cuidados. Ele não classifica mídias por tipo de empresa, setor, público ou suposta eficácia automática.",
}


def _copia(valor: Any) -> Any:
    return deepcopy(valor)


def listar_referencias() -> list[dict[str, Any]]:
    """Retorna autores, obras e capítulos/seções para estudo posterior."""
    return _copia(list(_REFERENCIAS))


def listar_analises() -> list[dict[str, Any]]:
    return _copia(list(_ANALISES))


def obter_analise(slug: str) -> dict[str, Any] | None:
    return _copia(next((item for item in _ANALISES if item["slug"] == slug), None))


def listar_segmentacoes() -> list[dict[str, Any]]:
    return _copia(list(_SEGMENTACOES))


def listar_categorias_midia() -> list[dict[str, Any]]:
    return _copia(list(_CATEGORIAS_MIDIA))


def listar_midias(categoria: str | None = None) -> list[dict[str, Any]]:
    """Lista mídias; ``categoria`` usa o slug público da categoria."""
    if categoria is None:
        itens = _MIDIAS
    else:
        categoria_normalizada = categoria.strip().upper()
        itens = tuple(item for item in _MIDIAS if item["categoria"] == categoria_normalizada)
    return _copia(list(itens))


def obter_midia(slug: str) -> dict[str, Any] | None:
    return _copia(next((item for item in _MIDIAS if item["slug"] == slug), None))


def obter_conteudo_educacional() -> dict[str, Any]:
    """Pacote único para uma tela de biblioteca ou exportação do manual."""
    return {
        "versao": 1,
        "referencias": listar_referencias(),
        "analises": listar_analises(),
        "segmentacoes": listar_segmentacoes(),
        "midias": listar_midias(),
        "categorias_midia": listar_categorias_midia(),
        "ressalvas": _copia(_CAVEATS),
    }


def obter_ressalvas() -> dict[str, str]:
    return _copia(_CAVEATS)
