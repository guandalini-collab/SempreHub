"""Catálogo fixo dos seis setores (aprovado pelo professor em 16/11/2026).

Cada item traz o preço de varejo efetivamente encontrado na pesquisa: mediana,
faixa central (Q1 a Q3), número de anúncios, fonte e data da coleta. Regras:
(a) valores verdadeiros, sem ajuste; (b) uma fonte só em cada escada de preços
do mesmo produto (tamanho, densidade, material); (c) produto sem evidência
fica fora do catálogo. Os relatórios completos estão no Projeto
(claude/pesquisa-setor1 a setor6).

O custo de compra da loja não está aqui: é calculado a partir do preço de
varejo pela taxa de margem da PAC 2024 da atividade e pela alíquota efetiva
do Simples Nacional (ver custos_catalogo.py).
"""

from __future__ import annotations

BUSCAPE = "Buscapé (menor oferta de cada anúncio)"
ML = "Mercado Livre, lojas oficiais"
RENNER = "Site da Renner (preço exibido, com promoções)"
MADEIRA = "MadeiraMadeira (títulos que informam o material)"
D15, D16 = "2026-11-15", "2026-11-16"

# Atividade da PAC 2024 (tabela 10645) usada para a taxa de margem de cada setor.
ATIVIDADE_PAC = {
    "colchoes": ("4754+4757+4759", "Móveis, iluminação e outros artigos de uso doméstico", 0.685, 7.7),
    "moveis": ("4754+4757+4759", "Móveis, iluminação e outros artigos de uso doméstico", 0.685, 7.7),
    "vestuario": ("4781", "Vestuário e complementos", 0.861, 6.3),
    "bicicletas": ("47.6", "Artigos culturais, recreativos e esportivos", 0.721, 6.5),
    "pet": ("4783+4785+4789", "Outros produtos novos e usados", 0.582, 13.2),
    "mochilas": ("4782", "Calçados, artigos de couro e de viagem", 0.701, 6.7),
}

SETORES = {
    "colchoes": "Colchões e Dormitório",
    "moveis": "Móveis Residenciais",
    "vestuario": "Vestuário e Moda Básica",
    "bicicletas": "Bicicletas e Mobilidade Leve",
    "pet": "Pet Shop",
    "mochilas": "Mochilas, Malas e Bolsas",
}


def _i(setor, linha, nome, mediana, q1, q3, n, fonte, data, unidade="unidade", aviso=None):
    return {"setor": setor, "linha": linha, "nome": nome, "preco_mediana": mediana,
            "preco_q1": q1, "preco_q3": q3, "n_anuncios": n, "fonte": fonte,
            "data_coleta": data, "unidade": unidade, "aviso": aviso}


def _escada(setor, linha, produto, tamanhos, valores, fonte, data, aviso=None):
    """Variações de tamanho do mesmo produto (uma fonte só)."""
    return [_i(setor, linha, f"{produto} {t}", *v, fonte, data, aviso=aviso)
            for t, v in zip(tamanhos, valores) if v]


TAM = ("solteiro", "casal", "queen", "king")
PEQ = "Amostra com menos de 10 anúncios."

ITENS: list[dict] = [
    # ---- Setor 1: Colchões e Dormitório (Buscapé 15/11/2026, salvo indicação)
    _i("colchoes", "Colchões", "Colchão de espuma D23 solteiro", 376, 350, 472, 13, BUSCAPE, D16),
    *_escada("colchoes", "Colchões", "Colchão de espuma D28", TAM,
             [(425, 378, 464, 21), (679, 578, 753, 19), (777, 719, 859, 12), (1128, 1005, 1405, 9)], BUSCAPE, D15),
    *_escada("colchoes", "Colchões", "Colchão de espuma D33", TAM,
             [(585, 495, 700, 17), (846, 653, 1068, 11), (1047, 877, 1475, 18), (1404, 1060, 1980, 8)], BUSCAPE, D15),
    *_escada("colchoes", "Colchões", "Colchão de espuma D45", TAM,
             [(715, 540, 903, 24), (1148, 863, 1343, 22), (1453, 1189, 1708, 23), (2064, 1792, 2639, 21)], BUSCAPE, D15),
    *_escada("colchoes", "Colchões", "Colchão de molas bonnel", TAM,
             [(709, 594, 813, 17), (1125, 835, 1433, 14), (1565, 1267, 2030, 16), (1968, 1748, 2559, 13)], BUSCAPE, D15),
    *_escada("colchoes", "Colchões", "Colchão de molas ensacadas", TAM,
             [(675, 511, 1187, 18), (1203, 973, 1615, 23), (1485, 1161, 1962, 20), (1977, 1691, 2348, 25)], BUSCAPE, D15),
    *_escada("colchoes", "Colchões", "Colchão viscoelástico", TAM,
             [(1080, 1052, 1085, 7), (1675, 1459, 2233, 9), (1936, 1798, 2460, 9), (2215, 2149, 3320, 8)], BUSCAPE, D15, PEQ),
    _i("colchoes", "Colchões", "Colchão viúvo de espuma", 1052, 721, 1715, 13, BUSCAPE, D15),
    _i("colchoes", "Colchões", "Colchão viúvo de molas ensacadas", 1129, 919, 1294, 23, ML, D16),
    *_escada("colchoes", "Bases", "Base box", TAM,
             [(228, 180, 258, 19), (360, 280, 432, 15), (388, 344, 577, 19), (764, 707, 1027, 10)], BUSCAPE, D15),
    *_escada("colchoes", "Bases", "Box baú", TAM[:3],
             [(470, 384, 514, 19), (660, 474, 920, 21), (1006, 967, 1325, 18)], BUSCAPE, D15),
    _i("colchoes", "Bases", "Box baú king", 1249, 1149, 1319, 24, ML, D16),
    _i("colchoes", "Complementos", "Travesseiro", 94, None, None, 18, BUSCAPE, D15),
    _i("colchoes", "Complementos", "Travesseiro viscoelástico", 128, None, None, 27, BUSCAPE, D15),
    _i("colchoes", "Complementos", "Protetor impermeável solteiro", 68, None, None, 14, BUSCAPE, D15),
    _i("colchoes", "Complementos", "Protetor impermeável casal", 67, None, None, 10, BUSCAPE, D15),

    # ---- Setor 2: Móveis Residenciais
    _i("moveis", "Sala", "Sofá de 2 lugares", 1016, 884, 1863, 23, BUSCAPE, D15),
    _i("moveis", "Sala", "Sofá de 3 lugares", 1404, 1054, 1923, 20, BUSCAPE, D15),
    _i("moveis", "Sala", "Sofá retrátil e reclinável", 2511, 1546, 3383, 15, BUSCAPE, D15),
    _i("moveis", "Sala", "Painel para TV", 318, 201, 404, 22, BUSCAPE, D15),
    _i("moveis", "Sala", "Mesa de centro", 325, 230, 1022, 12, BUSCAPE, D15),
    _i("moveis", "Cozinha", "Mesa de jantar com 6 cadeiras", 1200, 712, 2433, 16, BUSCAPE, D15),
    _i("moveis", "Cozinha", "Cadeira de jantar avulsa", 237, 177, 498, 21, BUSCAPE, D15),
    _i("moveis", "Cozinha", "Cozinha compacta modulada", 701, 552, 1146, 20, BUSCAPE, D15),
    _i("moveis", "Cozinha", "Armário aéreo de cozinha", 329, 219, 403, 22, BUSCAPE, D15),
    _i("moveis", "Escritório", "Escrivaninha ou mesa para computador", 320, 263, 453, 38, BUSCAPE, D15),
    _i("moveis", "Escritório", "Mesa em L", 467, 428, 816, 18, BUSCAPE, D15),
    _i("moveis", "Escritório", "Cadeira de escritório ergonômica", 587, 479, 728, 18, BUSCAPE, D15),
    _i("moveis", "Quarto", "Guarda-roupa de solteiro", 540, 461, 629, 27, BUSCAPE, D15),
    _i("moveis", "Quarto", "Cabeceira de casal", 422, 380, 517, 21, BUSCAPE, D15),
    _i("moveis", "Quarto", "Cama de casal", 564, 419, 715, 9, BUSCAPE, D15, PEQ),
    *[_i("moveis", linha, f"{p} em {m}", *v, MADEIRA, D15) for linha, p, vals in (
        ("Quarto", "Guarda-roupa de casal", ((1588, 1162, 2013, 49), (3500, 2975, 4550, 59), (5550, 4360, 7811, 40))),
        ("Sala", "Rack para TV", ((752, 542, 1246, 26), (1640, 1120, 2028, 50), (1745, 1379, 2081, 43))),
        ("Quarto", "Cômoda", ((815, 568, 1010, 43), (1000, 718, 1450, 52), (1639, 1360, 2548, 60))),
        ("Cozinha", "Mesa de jantar com 4 cadeiras", ((1153, 910, 1482, 23), (2466, 1522, 4210, 42), (3099, 2187, 4685, 56))),
    ) for m, v in zip(("MDP", "MDF", "madeira maciça"), vals)],

    # ---- Setor 3: Vestuário (Renner 15/11/2026; calça térmica pelo Mercado Livre)
    _i("vestuario", "Dia a Dia", "Camiseta básica masculina", 70, 59, 70, 16, RENNER, D15),
    _i("vestuario", "Dia a Dia", "Camiseta básica feminina", 40, 30, 57, 16, RENNER, D15),
    _i("vestuario", "Dia a Dia", "Camiseta infantil", 40, 30, 52, 16, RENNER, D15),
    _i("vestuario", "Dia a Dia", "Regata masculina", 50, 47, 60, 16, RENNER, D15),
    _i("vestuario", "Dia a Dia", "Bermuda de moletom masculina", 100, 72, 106, 16, RENNER, D15),
    _i("vestuario", "Jeans e Sarja", "Calça jeans masculina", 180, 180, 205, 16, RENNER, D15),
    _i("vestuario", "Jeans e Sarja", "Calça jeans feminina", 180, 180, 200, 16, RENNER, D15),
    _i("vestuario", "Jeans e Sarja", "Jaqueta jeans", 183, 140, 232, 16, RENNER, D15),
    _i("vestuario", "Jeans e Sarja", "Saia jeans", 61, 49, 91, 16, RENNER, D15),
    _i("vestuario", "Inverno", "Moletom (blusão)", 118, 102, 162, 14, RENNER, D15),
    _i("vestuario", "Inverno", "Casaco masculino", 133, 103, 160, 16, RENNER, D15),
    _i("vestuario", "Inverno", "Calça térmica masculina", 49, 33, 64, 16, ML, D16),

    # ---- Setor 4: Bicicletas
    _i("bicicletas", "Urbana e Passeio", "Bicicleta urbana", 783, 642, 1140, 20, BUSCAPE, D15),
    _i("bicicletas", "Urbana e Passeio", "Bicicleta dobrável", 2496, 1705, 2635, 6, ML, D16, PEQ),
    _i("bicicletas", "Urbana e Passeio", "Bicicleta infantil aro 16", 626, 589, 630, 26, BUSCAPE, D15),
    _i("bicicletas", "Urbana e Passeio", "Bicicleta infantil aro 20", 677, 630, 701, 18, BUSCAPE, D15),
    _i("bicicletas", "Esportiva", "Mountain bike aro 29 de entrada", 912, 900, 1351, 19, BUSCAPE, D15),
    _i("bicicletas", "Esportiva", "Mountain bike aro 29 com Shimano", 1003, 953, 1391, 15, BUSCAPE, D15),
    _i("bicicletas", "Performance", "Speed (estrada, aro 700)", 2399, 2399, 2518, 17, BUSCAPE, D15),
    _i("bicicletas", "Performance", "Mountain bike aro 29 de carbono", 18000, 14240, 21751, 8, ML, D16, PEQ),
    _i("bicicletas", "Elétrica", "Bicicleta elétrica de pedal assistido", 6999, 5349, 8799, 40, ML, D16,
       "Resolução Contran 996/2023: pedal assistido, sem acelerador, até 1.000 W e 32 km/h."),
    _i("bicicletas", "Complementos", "Capacete", 128, 98, 217, 13, BUSCAPE, D15),
    _i("bicicletas", "Complementos", "Caramanhola", 31, 19, 50, 18, BUSCAPE, D15),
    _i("bicicletas", "Complementos", "Cadeado", 23, 19, 48, 24, ML, D16),
    _i("bicicletas", "Complementos", "Bomba de ar manual", 49, 29, 88, 34, ML, D16),

    # ---- Setor 5: Pet Shop
    _i("pet", "Alimentação", "Ração seca super premium (pacote de 10 kg ou mais)", 16.33, 15.40, 22.93, 15, ML, D16, "kg",
       "Faixa declarada pelo fabricante; não é classificação oficial (IN MAPA 30/2009)."),
    _i("pet", "Alimentação", "Ração seca premium (pacote de 10 kg ou mais)", 12.27, 8.93, 13.07, 10, ML, D16, "kg",
       "Faixa declarada pelo fabricante; não é classificação oficial (IN MAPA 30/2009)."),
    _i("pet", "Alimentação", "Ração úmida em sachê", 32.16, 28.89, 35.95, 24, ML, D16, "kg"),
    _i("pet", "Alimentação", "Petisco", 29, 24, 34, 45, ML, D16, "embalagem"),
    _i("pet", "Conforto e passeio", "Caminha", 87, 35, 175, 13, BUSCAPE, D15),
    _i("pet", "Conforto e passeio", "Guia", 43, 32, 75, 26, BUSCAPE, D15),
    _i("pet", "Conforto e passeio", "Peitoral", 85, 65, 142, 25, BUSCAPE, D15),
    _i("pet", "Conforto e passeio", "Coleira", 44, 40, 45, 21, ML, D16),
    _i("pet", "Conforto e passeio", "Roupinha", 39, 31, 59, 41, ML, D16),
    _i("pet", "Conforto e passeio", "Casinha", 187, 43, 242, 18, BUSCAPE, D15),
    _i("pet", "Higiene", "Tapete higiênico", 63, 38, 79, 25, BUSCAPE, D15),
    _i("pet", "Higiene", "Areia sanitária", 46, 32, 60, 16, BUSCAPE, D15),
    _i("pet", "Higiene", "Shampoo", 114, 51, 185, 20, BUSCAPE, D15),
    _i("pet", "Complementos", "Brinquedo", 59, 56, 72, 11, BUSCAPE, D15),
    _i("pet", "Complementos", "Comedouro e bebedouro", 80, 34, 130, 20, BUSCAPE, D15),

    # ---- Setor 6: Mochilas, Malas e Bolsas
    _i("mochilas", "Escolar e Dia a Dia", "Mochila escolar", 110, 91, 167, 24, BUSCAPE, D15),
    _i("mochilas", "Escolar e Dia a Dia", "Mochila com rodinhas", 140, 117, 383, 10, BUSCAPE, D15),
    _i("mochilas", "Escolar e Dia a Dia", "Mochila para notebook", 128, 96, 182, 27, BUSCAPE, D15),
    _i("mochilas", "Viagem", "Mala de bordo rígida", 191, 166, 271, 27, ML, D16,
       "Mala de bordo: até 55 × 35 × 25 cm (regra das companhias aéreas)."),
    _i("mochilas", "Viagem", "Mala média rígida (23 kg)", 329, 279, 417, 21, ML, D16),
    _i("mochilas", "Viagem", "Mala grande rígida (32 kg)", 476, 445, 524, 20, ML, D16),
    _i("mochilas", "Viagem", "Mala de bordo de tecido", 280, 280, 755, 7, BUSCAPE, D15, PEQ),
    _i("mochilas", "Esportiva e Lazer", "Bolsa de academia", 127, 79, 167, 28, BUSCAPE, D15),
    _i("mochilas", "Esportiva e Lazer", "Pochete", 80, 49, 129, 17, BUSCAPE, D15),
    _i("mochilas", "Esportiva e Lazer", "Mochila térmica", 57, 47, 109, 39, ML, D16),
    _i("mochilas", "Bolsas", "Bolsa transversal sintética", 69, 66, 78, 15, ML, D16),
    _i("mochilas", "Bolsas", "Bolsa transversal de couro legítimo", 155, 94, 257, 32, ML, D16),
    _i("mochilas", "Bolsas", "Bolsa tote", 88, 57, 119, 18, BUSCAPE, D15),
    _i("mochilas", "Bolsas", "Clutch", 99, 63, 199, 24, BUSCAPE, D15),
    _i("mochilas", "Complementos", "Estojo escolar", 56, 56, 57, 17, BUSCAPE, D15),
    _i("mochilas", "Complementos", "Necessaire", 52, 42, 72, 22, BUSCAPE, D15),
    _i("mochilas", "Complementos", "Carteira masculina de couro", 85, 60, 103, 24, BUSCAPE, D15),
]


def _slug(texto: str) -> str:
    import unicodedata
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return "-".join("".join(c if c.isalnum() else " " for c in base).split())


for _item in ITENS:
    _item["id"] = f"{_item['setor']}-{_slug(_item['nome'])}"
assert len({i["id"] for i in ITENS}) == len(ITENS), "IDs repetidos no catálogo"


def catalogo(setor: str) -> list[dict]:
    return [dict(i) for i in ITENS if i["setor"] == setor]


def item(produto_id: str) -> dict | None:
    return next((dict(i) for i in ITENS if i["id"] == produto_id), None)
