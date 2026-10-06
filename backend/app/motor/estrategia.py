"""Coerência didática v1: premissas explícitas versus decisões e parâmetros.

Não classifica prosa nem inventa informações sobre o público. Penalidades
somadas até 20% afetam a conversão comercial uma única vez, sem débitos artificiais.
Planos antigos, sem análise estruturada, mantêm seu comportamento.
"""


def quadrante(crescimento, participacao):
    return ("ESTRELA" if participacao >= 1 else "INTERROGACAO") if crescimento >= 10 else ("VACA" if participacao >= 1 else "ABACAXI")


def avaliar(decisao, turma):
    plano = decisao.plano_comercial or {}
    analises = plano.get("analises")
    achados = []
    if not analises:
        return {"versao": 1, "fator": 1.0, "reducao": 0.0, "achados": [], "avaliada": False}

    def registrar(ferramenta, criterio, texto, peso):
        achados.append({"ferramenta": ferramenta, "criterio": criterio, "texto": texto, "reducao": peso})

    diretriz = analises.get("swot", {}).get("diretriz")
    if diretriz and diretriz != plano.get("posicionamento"):
        registrar("SWOT", "diretriz", "O posicionamento comercial diverge da diretriz escolhida na SWOT.", .04)
    rivalidade = analises.get("porter", {}).get("rivalidade", {}).get("intensidade")
    nivel = (turma.configuracao_simulacao or {}).get("nivel_concorrencia", "MEDIA")
    if rivalidade is not None and ((nivel == "ALTA" and rivalidade <= 3) or (nivel == "BAIXA" and rivalidade >= 8)):
        registrar("PORTER", "rivalidade", "A intensidade estimada da rivalidade contradiz o nível de concorrência do mercado da rodada.", .03)
    produto = next((p for p in analises.get("bcg", []) if p["produto_id"] == plano.get("produto_id")), None)
    if produto and produto["classificacao"] != quadrante(produto["crescimento"], produto["participacao"]):
        registrar("BCG", "quadrante", "A classificação do produto escolhido contradiz crescimento e participação informados na BCG (cortes: 10% e 1×).", .03)
    juros = analises.get("pestel", {}).get("juros_previstos")
    if juros is not None and decisao.emprestimo > 0 and abs(juros - turma.taxa_juros_mensal * 100) > 2:
        registrar("PESTEL", "juros", "O plano solicita crédito com uma premissa de juros divergente da taxa do mês em mais de 2 pontos percentuais.", .02)
    segmento = analises.get("segmentacao", {})
    teto = segmento.get("preco_maximo")
    if teto is not None and decisao.preco > teto:
        registrar("SEGMENTACAO", "preco", "O preço de venda supera o limite de compra declarado para o público-alvo.", .05)
    if segmento.get("cobertura") and segmento["cobertura"] != plano.get("cobertura"):
        registrar("SEGMENTACAO", "cobertura", "A cobertura do mix diverge da área escolhida para o público-alvo.", .03)
    if segmento.get("canais") and not set(segmento["canais"]) & set(plano.get("canais", [])):
        registrar("SEGMENTACAO", "canais", "Nenhum canal do mix corresponde aos canais de compra declarados para o público-alvo.", .04)
    if segmento.get("midias") and plano.get("midias") and not set(segmento["midias"]) & {m["id"] for m in plano["midias"]}:
        registrar("SEGMENTACAO", "midias", "O investimento em comunicação não alcança as mídias escolhidas na segmentação.", .04)
    reducao = min(.20, round(sum(a["reducao"] for a in achados), 4))
    return {"versao": 1, "fator": 1 - reducao, "reducao": reducao, "achados": achados, "avaliada": True}


def mensagens(avaliacao):
    if not avaliacao["achados"]:
        return []
    return [f"Alinhamento estratégico: redução de {avaliacao['reducao']:.0%} na conversão da demanda comercial (limite 20%)."] + [f"{a['ferramenta']}: {a['texto']}" for a in avaliacao["achados"]]
