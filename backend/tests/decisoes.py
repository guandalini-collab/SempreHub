"""Decisões completas para testes do motor, sem ocultar validações do contrato."""
from copy import deepcopy


def completar_decisao(dados):
    d = deepcopy(dados)
    d.setdefault("revisao_areas", {"decisoes":True,"financas":True,"producao":True,"logistica":True})
    d.setdefault("analise_financeira", "Conferimos margem, despesas, caixa e capital de giro conforme as escolhas desta rodada.")
    p = d.get("plano_comercial")
    if p:
        a = p.setdefault("analises", {})
        a.setdefault("swot", {}).setdefault("diretriz", p.get("posicionamento", "PRECO"))
        if a["swot"].get("diretriz") is None:
            a["swot"]["diretriz"] = p.get("posicionamento", "PRECO")
        segmento = a.setdefault("segmentacao", {})
        segmento.setdefault("geografica", ["Mercado local da simulação"])
        segmento.setdefault("canais", p.get("canais", ["DIRETO"]))
        segmento.setdefault("cobertura", p.get("cobertura", "LOCAL"))
        segmento.setdefault("preco_maximo", 100000)
        if not a.get("bcg"):
            produtos = p.get("produtos") or [{"produto_id": p["produto_id"], "produto_nome": "Produto do catálogo"}]
            a["bcg"] = [{"produto_id":x["produto_id"],"nome":x.get("produto_nome",x["produto_id"]),"crescimento":5,"participacao":1,"classificacao":"VACA","base":"PROJECAO","premissas":"Cenário didático definido pela equipe para comparar a execução da rodada."} for x in produtos]
    return d
