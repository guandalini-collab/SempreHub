"""Catálogo-base setorial e regras de aderência comercial.

Os setores e as categorias foram portados do Simula Marketing para que o
SempreHub não crie catálogos paralelos.  A tabela não substitui a pesquisa
oficial da rodada: ela define a estrutura operacional (linha, qualificação,
insumo, ocupação e mídia adequada) que torna o resultado do motor consistente
entre Marketing, RH, Produção e Logística.
"""

from __future__ import annotations

from copy import deepcopy


# Cada conjunto possui quatro categorias, como no Simula Marketing.  Valores
# financeiros, fontes e notícias continuam sendo trazidos pela edição de
# mercado; estes atributos são parâmetros didáticos de operação.
SETORES: dict[str, dict] = {
    "Eletrônicos e Tecnologia": {"id": "eletronicos", "categorias": [
        ("smartphone", "Smartphone", "INTERMEDIARIA", "tecnico", "componentes_mobile", 1.0, 1.0, 3000),
        ("tablet", "Tablet", "INTERMEDIARIA", "tecnico", "componentes_tablet", 1.0, 1.1, 3500),
        ("notebook", "Notebook", "PREMIUM", "especialista", "componentes_pc", 1.2, 1.4, 8000),
        ("smartwatch", "Smartwatch", "PREMIUM", "especialista", "componentes_wearable", 1.15, 0.5, 4500),
    ]},
    "Alimentos e Bebidas": {"id": "alimentos", "categorias": [
        ("refrigerante", "Refrigerante", "POPULAR", "operario", "insumos_bebida", 1.0, 1.0, 1500),
        ("suco-natural", "Suco natural", "INTERMEDIARIA", "tecnico", "frutas_e_embalagens", 1.05, 1.0, 2500),
        ("snack-saudavel", "Snack saudável", "PREMIUM", "tecnico", "insumos_snack", 1.1, 0.4, 3000),
        ("chocolate", "Chocolate", "INTERMEDIARIA", "operario", "cacau_e_embalagens", 1.0, 0.25, 1800),
    ]},
    "Vestuário e Moda": {"id": "moda", "categorias": [
        ("tenis-esportivo", "Tênis esportivo", "PREMIUM", "tecnico", "materiais_calcado", 1.15, 0.8, 5000),
        ("jaqueta", "Jaqueta", "INTERMEDIARIA", "operario", "tecidos_jaqueta", 1.0, 0.7, 2400),
        ("mochila", "Mochila", "INTERMEDIARIA", "operario", "tecidos_mochila", 1.0, 0.5, 1800),
        ("relogio-pulso", "Relógio de pulso", "PREMIUM", "especialista", "componentes_relogio", 1.15, 0.1, 4500),
    ]},
    "Cosméticos e Beleza": {"id": "cosmeticos", "categorias": [
        ("perfume", "Perfume", "PREMIUM", "tecnico", "essencias_e_vidros", 1.1, 0.08, 4000),
        ("creme-facial", "Creme facial", "PREMIUM", "tecnico", "ativos_cosmeticos", 1.1, 0.08, 3500),
        ("shampoo", "Shampoo", "POPULAR", "operario", "base_cosmetica", 1.0, 0.35, 1500),
        ("batom", "Batom", "INTERMEDIARIA", "tecnico", "pigmentos_cosmeticos", 1.05, 0.03, 2200),
    ]},
    "Móveis e Decoração": {"id": "moveis", "categorias": [
        ("sofa", "Sofá", "PREMIUM", "tecnico", "madeira_e_estofado", 1.2, 3.0, 7000),
        ("mesa-jantar", "Mesa de jantar", "INTERMEDIARIA", "operario", "madeira_mesa", 1.0, 2.0, 4500),
        ("luminaria", "Luminária", "INTERMEDIARIA", "tecnico", "componentes_luminaria", 1.05, 0.3, 2500),
        ("estante", "Estante", "POPULAR", "operario", "madeira_estante", 1.0, 1.4, 2800),
    ]},
    "Automotivo": {"id": "automotivo", "categorias": [
        ("oleo-motor", "Óleo de motor", "POPULAR", "operario", "lubrificantes", 1.0, 0.1, 1200),
        ("filtro-ar", "Filtro de ar", "INTERMEDIARIA", "operario", "elementos_filtrantes", 1.0, 0.05, 1400),
        ("pastilha-freio", "Pastilha de freio", "PREMIUM", "tecnico", "compostos_freio", 1.15, 0.08, 3500),
        ("amortecedor", "Amortecedor", "PREMIUM", "especialista", "componentes_suspensao", 1.2, 0.4, 6000),
    ]},
    "Esportes e Fitness": {"id": "esportes", "categorias": [
        ("tenis-corrida", "Tênis de corrida", "PREMIUM", "tecnico", "materiais_calcado", 1.15, 0.8, 5000),
        ("bicicleta", "Bicicleta", "PREMIUM", "especialista", "componentes_bicicleta", 1.2, 1.5, 7000),
        ("bola-futebol", "Bola de futebol", "POPULAR", "operario", "materiais_bola", 1.0, 0.2, 1200),
        ("smartband", "Smartband", "INTERMEDIARIA", "tecnico", "componentes_wearable", 1.1, 0.1, 3500),
    ]},
    "Saúde e Bem-estar": {"id": "saude", "categorias": [
        ("vitamina-c", "Vitamina C", "POPULAR", "tecnico", "insumos_suplemento", 1.05, 0.03, 2000),
        ("whey-protein", "Whey protein", "PREMIUM", "tecnico", "proteina_e_embalagem", 1.1, 0.5, 3500),
        ("omega-3", "Ômega 3", "INTERMEDIARIA", "tecnico", "oleos_e_capsulas", 1.05, 0.03, 2200),
        ("probiotico", "Probiótico", "PREMIUM", "especialista", "culturas_e_capsulas", 1.15, 0.03, 4500),
    ]},
    "Educação e Cursos": {"id": "educacao", "categorias": [
        ("curso-tecnico", "Curso técnico", "INTERMEDIARIA", "tecnico", "conteudo_didatico", 1.0, 0.0, 1500),
        ("graduacao-ead", "Graduação EAD", "PREMIUM", "especialista", "plataforma_e_conteudo", 1.15, 0.0, 6000),
        ("graduacao-presencial", "Graduação presencial", "PREMIUM", "especialista", "corpo_docente", 1.2, 0.0, 8000),
        ("pos-graduacao", "Pós-graduação", "PREMIUM", "especialista", "conteudo_avancado", 1.2, 0.0, 7000),
    ]},
    "Pet Care": {"id": "pets", "categorias": [
        ("racao-premium", "Ração premium", "PREMIUM", "tecnico", "insumos_racao", 1.1, 0.5, 3000),
        ("petisco", "Petisco", "POPULAR", "operario", "insumos_petisco", 1.0, 0.08, 1200),
        ("brinquedo-pet", "Brinquedo pet", "INTERMEDIARIA", "operario", "materiais_brinquedo", 1.0, 0.2, 1600),
        ("caminha", "Caminha pet", "INTERMEDIARIA", "operario", "tecidos_e_espuma", 1.0, 0.7, 2200),
    ]},
    "Construção e Materiais": {"id": "construcao", "categorias": [
        ("cimento", "Cimento", "POPULAR", "operario", "clinquer_e_embalagem", 1.0, 0.04, 2500),
        ("tinta-latex", "Tinta látex", "INTERMEDIARIA", "tecnico", "resinas_e_pigmentos", 1.05, 0.1, 2200),
        ("porcelanato", "Porcelanato", "PREMIUM", "especialista", "argila_e_esmaltes", 1.2, 0.3, 5500),
        ("torneira", "Torneira", "PREMIUM", "tecnico", "metais_e_componentes", 1.15, 0.1, 3800),
    ]},
    "Entretenimento e Mídia": {"id": "entretenimento", "categorias": [
        ("streaming-video", "Streaming de vídeo", "INTERMEDIARIA", "tecnico", "infraestrutura_digital", 1.0, 0.0, 2500),
        ("streaming-musica", "Streaming de música", "POPULAR", "tecnico", "licencas_de_conteudo", 1.0, 0.0, 2000),
        ("jogo-digital", "Jogo digital", "PREMIUM", "especialista", "desenvolvimento_jogo", 1.2, 0.0, 7000),
        ("ingresso-show", "Ingresso para show", "PREMIUM", "tecnico", "producao_evento", 1.1, 0.0, 5000),
    ]},
}


# IDs existentes em catalogo_campanhas.py.  A faixa é uma regra de aderência:
# publicidade incompatível ainda é cobrada, mas não agrega atração ao produto.
MIDIAS_POR_LINHA = {
    "POPULAR": {"radio-spot", "radio-testemunhal", "flyer-impressao", "flyer-distribuicao", "carro-som", "sms", "outdoor", "busdoor", "tv15"},
    "INTERMEDIARIA": {"meta", "google", "influenciador-micro", "tv15", "outdoor", "painel", "feed", "stories", "carrossel", "colecao", "conteudo"},
    "PREMIUM": {"google", "influenciador-medio", "influenciador-grande", "podcast", "revista-inteira", "assessoria", "release", "cinema", "leaderboard", "native", "conteudo"},
}


def setores_disponiveis() -> list[str]:
    return list(SETORES)


def especificacao_produto(setor: str, produto_id: str, indice: int = 0) -> dict:
    """Retorna a ficha operacional da categoria ou uma ficha segura de fallback.

    Pesquisas oficiais podem nomear o item de forma diferente. Nesse caso o
    índice mantém a edição utilizável, mas a ficha é marcada como estimativa
    do modelo para nunca simular uma especificação externa como fato.
    """
    dados = SETORES.get(setor)
    if dados:
        for item in dados["categorias"]:
            if item[0] == produto_id:
                _, nome, linha, qualificacao, insumo, setup, m3, capex = item
                return {"nome_referencia": nome, "linha_produto": linha,
                        "qualificacao_minima": qualificacao, "insumo_chave": insumo,
                        "fator_setup": setup, "volume_armazenagem_m3": m3,
                        "capex_ativacao": capex, "midias_recomendadas": sorted(MIDIAS_POR_LINHA[linha]),
                        "fonte_especificacao": "Parâmetro didático setorial baseado no catálogo Simula Marketing"}
        item = dados["categorias"][indice % len(dados["categorias"])]
        _, nome, linha, qualificacao, insumo, setup, m3, capex = item
        return {"nome_referencia": nome, "linha_produto": linha,
                "qualificacao_minima": qualificacao, "insumo_chave": insumo,
                "fator_setup": setup, "volume_armazenagem_m3": m3,
                "capex_ativacao": capex, "midias_recomendadas": sorted(MIDIAS_POR_LINHA[linha]),
                "fonte_especificacao": "Estimativa do modelo: categoria equivalente do catálogo setorial"}
    return {"nome_referencia": produto_id, "linha_produto": "INTERMEDIARIA",
            "qualificacao_minima": "operario", "insumo_chave": f"insumo_{produto_id}",
            "fator_setup": 1.0, "volume_armazenagem_m3": 0.5, "capex_ativacao": 2000,
            "midias_recomendadas": sorted(MIDIAS_POR_LINHA["INTERMEDIARIA"]),
            "fonte_especificacao": "Estimativa do modelo: setor ainda sem ficha operacional"}


def enriquecer_produto(setor: str, produto: dict, indice: int = 0) -> dict:
    resultado = deepcopy(produto)
    especificacao = especificacao_produto(setor, str(produto.get("id", "")), indice)
    for chave, valor in especificacao.items():
        resultado.setdefault(chave, valor)
    return resultado
