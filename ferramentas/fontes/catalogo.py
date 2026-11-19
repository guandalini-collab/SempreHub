"""Códigos das séries, tabelas e NCM usados pelo SempreHub, com a situação de cada um.

situacao:
- "conferido": código conferido em fonte primária (página do órgão) ou já em uso no
  backend do SempreHub com resposta validada;
- "conferido_secundario": código conferido em fonte secundária (tabela NCM de
  terceiros, cliente de API de terceiros) — confirmar no primeiro uso;
- "resolver_por_nome": o código da categoria é descoberto em tempo de execução nos
  metadados oficiais do SIDRA, pelo nome, e registrado na saída.
O comando ``python -m fontes conferir`` testa cada entrada contra a API real.
"""

SGS = {
    # código: (nome oficial, periodicidade, situação, página de conferência)
    432: ("Taxa de juros - Meta Selic definida pelo Copom", "diária", "conferido",
          "em uso em backend/app/atualizacoes_oficiais.py"),
    4390: ("Taxa de juros - Selic acumulada no mês", "mensal", "conferido",
           "em uso em backend/app/mercado_pac.py"),
    1: ("Taxa de câmbio - Livre - Dólar americano (venda) - diário", "diária", "conferido",
        "https://dadosabertos.bcb.gov.br/dataset/1-taxa-de-cambio---livre---dolar-americano-venda---diario"),
    20714: ("Taxa média de juros das operações de crédito - Total", "mensal", "conferido",
            "https://dadosabertos.bcb.gov.br/dataset/20714-taxa-media-de-juros-das-operacoes-de-credito---total"),
    20740: ("Taxa média de juros das operações de crédito com recursos livres - Pessoas físicas - Total",
            "mensal", "conferido",
            "https://dadosabertos.bcb.gov.br/dataset/20740-taxa-media-de-juros-das-operacoes-de-credito-com-recursos-livres---pessoas-fisicas---total"),
    20750: ("Taxa média de juros das operações de crédito com recursos livres - Pessoas físicas - Aquisição de outros bens",
            "mensal", "conferido",
            "https://dadosabertos.bcb.gov.br/dataset/20750-taxa-media-de-juros-das-operacoes-de-credito-com-recursos-livres---pessoas-fisicas---aquisica"),
    20741: ("Taxa média de juros ... recursos livres - Pessoas físicas - Cheque especial", "mensal", "conferido",
            "https://dadosabertos.bcb.gov.br/dataset/20741-taxa-media-de-juros-das-operacoes-de-credito-com-recursos-livres---pessoas-fisicas---cheque-e"),
    29037: ("Endividamento das famílias com o SFN em relação à renda acumulada dos últimos doze meses (RNDBF)",
            "mensal", "conferido",
            "https://dadosabertos.bcb.gov.br/dataset/29037-endividamento-das-familias-com-o-sistema-financeiro-nacional-em-relacao-a-renda-acumulada-dos"),
    433: ("Índice nacional de preços ao consumidor-amplo (IPCA) - variação mensal", "mensal",
          "conferido_secundario", "valorfinal.com.br/custo-de-vida/indicadores (secundária); preferir SIDRA 7060"),
}

# IPCA pelo IBGE (fonte produtora). Variável 63 = variação mensal (em uso no backend).
IPCA = {"tabela": 7060, "variavel_mensal": 63, "classificacao": 315, "situacao": "conferido",
        "conferencia": "em uso em backend/app/ipca_catalogo.py",
        # Variável de 12 meses: descoberta pelo nome nos metadados ("acumulada em 12 meses").
        "variavel_12m": "resolver_por_nome"}

# Pesquisa Mensal de Comércio (IBGE). Classificação 11046 = tipo de índice; 85 = atividades.
PMC = {
    "volume": {"tabela": 8882, "variavel": 7169, "tipo_indice": 56734, "situacao": "conferido",
               "conferencia": "em uso em backend/app/motor/sazonalidade_pmc.py"},
    "receita_nominal": {"tabela": 8883, "variavel": 7169, "tipo_indice": 56735, "situacao": "conferido",
                        "conferencia": "em uso em backend/app/mercado_pac.py"},
    "atividades": {31555: "Móveis", 90673: "Tecidos, vestuário e calçados",
                   103158: "Outros artigos de uso pessoal e doméstico"},
}

# Pesquisa Industrial Mensal - Produção Física (IBGE). Atividades resolvidas pelo nome.
PIM = {"tabela": 8888, "situacao_tabela": "conferido_secundario",
       "conferencia": "valorfinal.com.br (secundária): tabela 8888, variáveis 12606/12607; confirmar nos metadados",
       "atividades_por_nome": {
           "vestuario": ["confecção de artigos do vestuário", "fabricação de produtos têxteis"],
           "colchoes": ["fabricação de móveis"],
           "moveis": ["fabricação de móveis"],
           "bicicletas": ["outros equipamentos de transporte"],
           "mochilas": ["artefatos de couro", "artigos para viagem"],
       }}

# Comex Stat (MDIC): filtros "chapter" (2 dígitos), "position" (4), "subposition" (6), "ncm" (8).
COMEX = {
    "vestuario": {"chapter": [61, 62], "situacao": "conferido_secundario",
                  "nota": "Cap. 61 (malha) e 62 (exceto malha) do Sistema Harmonizado"},
    "colchoes": {"ncm": [94042100, 94042900], "situacao": "conferido_secundario",
                 "nota": "9404.21.00 borracha/plástico alveolar; 9404.29.00 de outras matérias"},
    "moveis": {"position": [9401, 9403], "situacao": "conferido_secundario",
               "nota": "9401 assentos; 9403 outros móveis"},
    "bicicletas": {"ncm": [87120010, 87116000],
                   "subposition": [871491, 871492, 871493, 871494, 871495, 871496, 871499],
                   "situacao": "conferido_secundario",
                   "nota": "8712.00.10 bicicletas; 8711.60.00 com motor elétrico (inclui outros veículos elétricos "
                           "de duas rodas); 8714.91-99 partes de bicicletas — subposições a conferir"},
    "pet": {"ncm": [23091000], "situacao": "conferido_secundario",
            "nota": "2309.10.00 alimentos para cães ou gatos, acondicionados para venda a retalho"},
    "mochilas": {"subposition": [420211, 420212, 420219, 420292], "situacao": "conferido_secundario",
                 "nota": "4202.1x malas; 4202.92 superfície exterior de plástico ou têxtil (inclui mochilas)"},
}

# Boletim Focus (BCB, Olinda/OData). Nomes de indicador conforme a API.
FOCUS = {"base": "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/",
         "anuais": "ExpectativasMercadoAnuais", "indicadores": ["IPCA", "Selic", "Câmbio", "PIB Total"],
         "situacao": "conferido_secundario",
         "conferencia": "pacote rbcb (CRAN), odata-expectativas.R; página de dados abertos do BCB"}

# Fontes sem API: monitoramento de página (detecta publicação nova); números só entram após conferência.
PAGINAS = {
    "colchoes": [("ABICOL", "https://www.abicol.org.br")],
    "moveis": [("ABIMÓVEL", "https://abimovel.com")],
    "vestuario": [("ABIT", "https://www.abit.org.br"), ("ABVTEX", "https://www.abvtex.org.br")],
    "bicicletas": [("ABRACICLO", "https://www.abraciclo.com.br"), ("Aliança Bike", "https://aliancabike.org.br")],
    "pet": [("ABEMPET", "https://abempet.org.br")],
    "mochilas": [("ABIACAV", "https://www.abiacav.org.br")],
}
# Domínios de PAGINAS: só ABIT, ABVTEX, ABRACICLO, Aliança Bike e ABEMPET constam de
# backend/app/fontes_oficiais.py (conferidos em 14/11/2026); os demais estão a conferir.
