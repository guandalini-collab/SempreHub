"""Referências públicas de serviços. Tarifas de veiculação do jogo não mudam.

Preço publicado «a partir de» é um piso de referência, não uma cotação universal.
Escopos adaptados para o jogo são identificados; serviços já incluídos no pacote
não são cobrados duas vezes. Evidências e limitações: docs/fontes-servicos-midias.md.
"""
from copy import deepcopy

CONSULTA='07/10/2026'
FONTES={
 'vt':dict(titulo='Toranja Films · publicidade e criativos',url='https://www.toranjafilms.com/servicos/publicidade-e-criativos/',trecho='A partir de R$ 3.000; filme principal master (15s, 30s ou 60s).'),
 'motion':dict(titulo='Two Pixels · produção de vídeo',url='https://www.twopixels.com.br/producao-de-video-com-ia/',trecho='Motion 15–30s — R$ 990+.'),
 'impresso':dict(titulo='Tabela de serviços Be It · documento público',url='https://pt.scribd.com/document/849457514/Tabela-de-Servic-os-Be-It',trecho='Anúncio revista/jornal: 1/4 página 580,90; 1/2 página 780,90; 1 página 850,20; página dupla 1.200,00. Data editorial não informada.'),
 'flyer':dict(titulo='ADM Agência · design gráfico',url='https://admagenciadigital.com.br/tabela-de-precos-de-design-grafico/',trecho='Flyer/Panfleto até A4: R$ 350. Não somos gráfica e os custos de impressão não estão inclusos.'),
 'audio':dict(titulo='GT Studio · spot comercial',url='https://www.gtstudio.com.br/spot-para-radio-gravacao-de-spots-comerciais.html',trecho='Spot simples a partir de R$ 199,00: locução e trilha.'),
 'lona':dict(titulo='BannerJÁ · painel em lona',url='https://www.bannerja.com.br/categoria/painel-lona',trecho='Painel em lona simples: a partir de R$ 46/m².'),
}
for fonte in FONTES.values():fonte['data_consulta']=CONSULTA


def servico(midia,nome,preco,fonte,escopo,cobranca='POR_CAMPANHA',tipo='Preço publicado de referência; contratação real sujeita ao escopo e orçamento.'):
    return dict(id='servico-'+midia,nome=nome,preco_unitario=preco,unidade='serviço',cobranca=cobranca,escopo=escopo,fonte=FONTES[fonte],referencia_tipo=tipo)

SERVICOS={}
for midia,preco in {'jornal-inteira':850.20,'revista-inteira':850.20,'jornal-meia':780.90,'revista-meia':780.90,'jornal-dupla':1200,'revista-dupla':1200,'jornal-fracao':580.90,'revista-fracao':580.90}.items():
    SERVICOS[midia]=[servico(midia,'Criação e fechamento da arte impressa',preco,'impresso','Uma peça no formato contratado. Fração considera 1/4 de página. Tabela pública sem data de vigência informada; referência para o exercício.')]
SERVICOS['flyer-impressao']=[servico('flyer-impressao','Design do panfleto até A4',350,'flyer','Criação da arte; impressão e distribuição são contratadas nas linhas próprias.')]
for midia in ('tv15','tv30','cinema','teaser'):
    SERVICOS[midia]=[servico(midia,'Produção do filme publicitário',3000,'vt','Piso publicado para filme publicitário básico. Inclui produção audiovisual do projeto; não presume direitos irrestritos de imagem, música ou adaptações para cinema. Licenças e exigências de exibição dependem do orçamento real.',tipo='A partir de R$ 3.000 por projeto; referência básica, não orçamento de produção cinematográfica premium.')]
for midia in ('bumper','skippable','stories','painel','telas','vinheta'):
    SERVICOS[midia]=[servico(midia,'Criação de vídeo / motion',990,'motion','Referência publicada para motion de 15–30s. No jogo, uma peça adaptada ao formato; bumper, vinheta e telas exigem versão curta. Não equivale a filmagem com atores.',tipo='A partir de R$ 990; adaptação didática da referência de motion 15–30s.')]
for midia in ('radio-spot','radio-streaming','carro-som'):
    SERVICOS[midia]=[servico(midia,'Produção de áudio · locução e trilha',199,'audio','Spot simples. Cachês especiais, trilhas exclusivas e efeitos complexos não fazem parte deste piso.',tipo='Preço publicado a partir de R$ 199; peça simples de áudio.')]
# Metragens são premissas visíveis do exercício, não dimensões de toda instalação real.
SERVICOS['outdoor']=[servico('outdoor','Impressão de lona · 9 × 3 m',1242,'lona','27 m² × R$ 46/m². Somente impressão. Fixação, projeto de arte e licenças dependem de orçamento; não estão comprovados por esta referência.','POR_UNIDADE_MIDIA',tipo='Preço publicado por m²; 9 × 3 m é uma premissa didática explícita.')]
SERVICOS['frontlight']=[servico('frontlight','Impressão de lona · 9 × 3 m',1242,'lona','27 m² × R$ 46/m², lona simples para iluminação frontal. Não é lona translúcida de backlight. Instalação e licenças exigem orçamento próprio.','POR_UNIDADE_MIDIA',tipo='Referência de lona simples; dimensão assumida pelo exercício, não cotação de frontlight instalado.')]

DEPENDENCIAS={
 'flyer-impressao':'Contratar impressão e distribuição na mesma quantidade. O design é cobrado uma vez por produto e mês.',
 'flyer-distribuicao':'Exige impressão na mesma quantidade; distribuição não inclui arte nem impressão.',
 'jingle':'Produção sem audiência: exige veiculação em rádio ou streaming. Substitui a produção de spot simples quando contratado junto.',
}
INCLUIDOS={
 'influenciador-micro':'Pacote didático de parceria, incluindo criação pelo influenciador. Direitos de reutilização e envio de produtos podem exigir orçamento adicional.',
 'influenciador-medio':'Pacote didático de parceria, incluindo criação pelo influenciador. Direitos de reutilização e envio de produtos podem exigir orçamento adicional.',
 'influenciador-grande':'Pacote didático de parceria, incluindo criação pelo influenciador. Direitos de reutilização e envio de produtos podem exigir orçamento adicional.',
 'conteudo':'Pacote mensal do jogo inclui a produção básica de conteúdo.',
 'jingle':'A tarifa original já é a produção do jingle; não inclui veiculação.',
 'flyer-impressao':'Tarifa original por unidade de impressão. Arte e distribuição são separadas.',
 'flyer-distribuicao':'Tarifa original por unidade distribuída. Arte e impressão são separadas.',
 'radio-testemunhal':'Pacote do jogo inclui leitura ao vivo; a equipe deve preparar briefing e texto. Não inclui produção de spot gravado.',
 'mala':'Pacote do jogo inclui impressão e postagem da peça.',
 'telemarketing':'Pacote mensal do jogo inclui operação básica terceirizada.',
 'assessoria':'Honorários mensais do serviço de assessoria; não garantem publicação.',
 'release':'Pacote do jogo inclui redação e envio do comunicado.',
 'brindes':'Pacote didático de brinde básico personalizado por unidade; itens especiais e frete variam.',
 'push':'Licença do serviço; não garante audiência nem inclui desenvolvimento de aplicativo.',
}
PENDENTES={
 'busdoor':'Vinil perfurado, criação e aplicação na garagem.',
 'mobiliario':'Arte, impressão no formato e instalação.',
 'empena':'Arte, lona de grande formato, projeto e instalação especializada em altura.',
 'frota':'Projeto, adesivo apropriado, preparação e aplicação em veículo.',
 'infocomercial':'Roteiro, captação e edição de filme de 15–30 minutos; não usar preço de VT de 30 segundos.',
 'merchandising':'Amostras, frete, briefing e apoio técnico; variam conforme produto e emissora.',
 'placement':'Amostras, frete e direitos de uso; negociação com a produção audiovisual.',
 'placement-premium':'Amostras, frete e direitos de uso; negociação com a produção audiovisual.',
}


def servicos_por_midia(midia):return deepcopy(SERVICOS.get(midia,[]))


def metadados(midia):
    servicos=servicos_por_midia(midia)
    escopo=INCLUIDOS.get(midia,'A tarifa original do jogo remunera o espaço/pacote descrito, não uma cotação universal de campanha completa.')
    pendente=PENDENTES.get(midia)
    return dict(servicos_obrigatorios=servicos,escopo_pacote=escopo,dependencias=DEPENDENCIAS.get(midia),custos_sob_consulta=pendente)

# Complemento de pesquisa com páginas de fornecedores abertas.
FONTES.update({
 'social':dict(titulo='Estúdio Belize · redes sociais',url='https://www.estudiobelize.com.br/redes-sociais',trecho='Arte de Post Instagram - Unitária R$ 80,00; Arte para Carrossel Instagram R$ 120,00.',data_consulta=CONSULTA),
 'google':dict(titulo='DivulgaAI · gestão Google Ads',url='https://divulgaai.com.br/',trecho='Gestão Google Ads: R$ 297/mês; verba de mídia paga diretamente ao Google.',data_consulta=CONSULTA),
 'email':dict(titulo='We Do Logos · layout de e-mail marketing',url='https://www.wedologos.com.br/comprar/layoutemailmkt.aspx',trecho='Projeto de E-mail Marketing pelo valor de R$ 545,00; um email marketing sem html.',data_consulta=CONSULTA),
 'outdoor-arte':dict(titulo='Imprima Aqui · outdoor 9×3',url='https://imprimaaqui.com.br/produto/comprar/1/outdoor-9x3',trecho='Criação de arte: R$ 150,00 uni.',data_consulta=CONSULTA),
})
SERVICOS['google']=[servico('google','Gestão de campanha Google Ads',297,'google','Referência de honorários mensais; verba paga ao Google é separada. No jogo, gestão por campanha de produto e mês.')]
SERVICOS['email']=[servico('email','Design do e-mail marketing',545,'email','Desenho de um e-mail, sem HTML. O pacote de envios do jogo fornece a ferramenta com editor visual; programação personalizada não está incluída.')]
for midia in ('feed','radio-social','colecao','leaderboard','mpu','halfpage','skyscraper','billboard','interstitial','native'):
    SERVICOS[midia]=[servico(midia,'Design da peça digital',80,'social','Referência de uma arte estática para rede social. No jogo, adaptação ao formato contratado; não inclui fotografia profissional, programação ou produção de vídeo.',tipo='Arte unitária publicada a R$ 80; adaptação didática para formatos digitais estáticos.')]
SERVICOS['carrossel']=[servico('carrossel','Design do carrossel',120,'social','Arte de carrossel; não inclui ensaio fotográfico ou filmagem.')]
for midia in ('outdoor','frontlight'):
    SERVICOS[midia].append(servico(midia+'-arte','Criação de arte para painel',150,'outdoor-arte','Uma arte para o painel de 9 × 3 m. Instalação é orçada separadamente.'))
PENDENTES.update({
 'outdoor':'Fixação e instalação da lona de 9 × 3 m.',
 'frontlight':'Fixação e instalação do painel de 9 × 3 m.',
 'meta':'Gestão de campanha e criação das peças não incluídas na verba de mídia.',
})
# Sem inventar preço para escopos sem tarifa pública: cotação obrigatória e
# identificada como informada pela equipe, distinta das referências pesquisadas.
# Nenhuma compra desses formatos é aceita apenas com verba de veiculação.
