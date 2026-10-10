"""Relatório pedagógico a partir dos registros efetivamente encerrados.

Os indicadores usam os snapshots de cada rodada. Não recalculamos resultados
antigos com parâmetros atuais nem fabricamos balanços para o motor legado.
"""

from .motor.versionamento import versao_snapshot, snapshot_para_leitura

from copy import deepcopy
import csv
import io
import json
import math

from . import serializacao as ser
from .models import Turma


PESOS_PADRAO = {"lucro": 0.4, "patrimonio": 0.3, "satisfacao": 0.2, "participacao": 0.1}


def _numero(valor):
    if isinstance(valor, bool) or not isinstance(valor, (float, int)):
        return None
    return float(valor) if math.isfinite(valor) else None


def _razao(numerador, denominador):
    numerador, denominador = _numero(numerador), _numero(denominador)
    if numerador is None or denominador is None or denominador <= 0:
        return None
    return numerador / denominador


def _objeto(valor):
    return valor if isinstance(valor, dict) else {}


def _iso(data):
    return data.isoformat() + "Z" if data is not None else None


def _membros(empresa):
    if empresa.turma.modo_equipe:
        return [
            {"aluno_id": m.aluno_id, "nome": m.aluno.nome, "cargos": list(m.cargos or [])}
            for m in empresa.membros
        ]
    return [{"aluno_id": empresa.aluno_id, "nome": empresa.aluno.nome, "cargos": []}]


def _participacao(empresa, decisao, rodada):
    registros = [r for r in empresa.registros_equipe if r.rodada == rodada]
    assinaturas = [
        {
            "aluno_id": a.aluno_id,
            "nome": a.aluno.nome,
            "versao": a.versao,
            "aprovado_em": _iso(a.aprovado_em),
            "conteudo": deepcopy(a.conteudo),
        }
        for a in (decisao.aprovacoes if decisao else [])
    ]
    versao = decisao.versao if decisao else None
    validas = [a for a in assinaturas if a["versao"] == versao]
    membros = _membros(empresa)
    # A composição assinada prevalece sobre a atual para a leitura histórica.
    if validas:
        composicao = validas[0]["conteudo"].get("membros")
        if isinstance(composicao, list):
            nomes = {m["aluno_id"]: m["nome"] for m in membros}
            nomes.update({a["aluno_id"]: a["nome"] for a in assinaturas})
            membros = [
                {"aluno_id": m["aluno_id"], "nome": nomes.get(m["aluno_id"], "Aluno"), "cargos": list(m.get("cargos") or [])}
                for m in composicao if isinstance(m, dict) and "aluno_id" in m
            ]
    acoes = [
        {
            "aluno_id": r.aluno_id, "nome": r.aluno.nome, "acao": r.acao,
            "rodada": r.rodada, "versao": r.versao, "data": _iso(r.data),
            "detalhes": {**deepcopy(r.detalhes or {}), "autor_conceito": "Professor Guandalini"},
        }
        for r in registros
    ]
    ids_confirmados = {a["aluno_id"] for a in validas}
    equipe = bool(empresa.turma.modo_equipe)
    for membro in membros:
        membro["confirmou_versao"] = membro["aluno_id"] in ids_confirmados if equipe else None
        membro["assinaturas"] = [a for a in assinaturas if a["aluno_id"] == membro["aluno_id"]]
        membro["acoes"] = [a for a in acoes if a["aluno_id"] == membro["aluno_id"]]
    envio_lider = next((a for a in validas if a["conteudo"].get("tipo") == "ENVIO_LIDER"), None)
    if equipe and envio_lider:
        proporcao = float(bool(decisao.enviada_em and not decisao.automatica))
        for membro in membros:
            membro["confirmou_versao"] = None
    elif equipe:
        proporcao = len(ids_confirmados.intersection(m["aluno_id"] for m in membros)) / len(membros) if membros else None
    else:
        # Entrega individual autenticada é evidência; não inventar uma assinatura.
        proporcao = float(bool(decisao and not decisao.automatica and decisao.enviada_em))
    return {
        "tipo": "EQUIPE" if equipe else "INDIVIDUAL",
        "modo_envio": "LIDER" if envio_lider else "CONFIRMACOES" if equipe else "INDIVIDUAL",
        "lider_id": envio_lider["aluno_id"] if envio_lider else None,
        "proporcao_confirmada": proporcao,
        "membros": membros, "assinaturas": assinaturas, "acoes": acoes,
    }


def indicadores_rodada(resultado, detalhes):
    detalhes = _objeto(detalhes)
    balanco = _objeto(detalhes.get("balanco"))
    inicial = _objeto(detalhes.get("estado_inicial"))
    final = _objeto(detalhes.get("estado_final"))
    operacao = _objeto(detalhes.get("operacao"))
    # ROE usa o patrimônio de abertura congelado, nunca o caixa atual da empresa.
    patrimonio_inicial = _numero(inicial.get("patrimonio"))
    if patrimonio_inicial is None and balanco:
        # O motor também pode fornecer o balanço de abertura dentro do snapshot.
        patrimonio_inicial = _numero(_objeto(detalhes.get("balanco_inicial")).get("patrimonio"))
    if patrimonio_inicial is None and balanco:
        patrimonio_final = _numero(balanco.get("patrimonio"))
        aportes = _numero(final.get("capital_aportado"))
        aportes_iniciais = _numero(inicial.get("capital_aportado"))
        lucro = _numero(resultado.lucro_liquido)
        if None not in (patrimonio_final, aportes, aportes_iniciais, lucro):
            patrimonio_inicial = patrimonio_final - lucro - (aportes - aportes_iniciais)
    ativos = None
    passivos = None
    if balanco:
        partes = [_numero(balanco.get(k)) for k in ("caixa", "receber", "estoques", "imobilizado")]
        obrigacoes = [_numero(balanco.get(k)) for k in ("pagar", "divida")]
        if all(v is not None for v in partes + obrigacoes):
            ativos = max(0.0, partes[0]) + sum(partes[1:])
            passivos = sum(obrigacoes) + max(0.0, -partes[0])
    satisfacao = _numero(final.get("satisfacao"))
    if satisfacao is None:
        satisfacao = _numero(operacao.get("satisfacao"))
    return {
        "margem_liquida": _razao(resultado.lucro_liquido, resultado.receita),
        "endividamento": _razao(passivos, ativos),
        "roe": _razao(resultado.lucro_liquido, patrimonio_inicial),
        "capital_giro": _numero(balanco.get("capital_giro")),
        "satisfacao": satisfacao,
        "cac": _numero(operacao.get("cac", operacao.get("CAC"))),
        "ltv": _numero(operacao.get("ltv", operacao.get("LTV"))),
        "churn": _numero(operacao.get("churn")),
        "runway": _numero(operacao.get("runway")),
    }


def _rodada(empresa, resultado, decisao):
    detalhes = snapshot_para_leitura(getattr(resultado, "detalhes_simulacao", None))
    snapshot = _objeto(detalhes)
    basico = ser.resultado(resultado)
    dre = dict(basico["dre"])
    dre.update(_objeto(snapshot.get("dre")))
    return {
        "rodada": resultado.rodada,
        "modo": snapshot.get("modo", "LEGADO"),
        "engine_version": versao_snapshot(snapshot),
        "preco": resultado.preco,
        "demanda": resultado.demanda,
        "unidades_vendidas": resultado.unidades_vendidas,
        "participacao_mercado": resultado.participacao_mercado,
        "dre": dre,
        "dfc": deepcopy(snapshot.get("dfc")),
        "balanco": deepcopy(snapshot.get("balanco")),
        "operacao": deepcopy(snapshot.get("operacao")),
        "indicadores": indicadores_rodada(resultado, detalhes),
        "decisao": ser.decisao(decisao),
        "participacao": _participacao(empresa, decisao, resultado.rodada),
        "alertas": list(resultado.alertas or []),
        "detalhes_simulacao": detalhes,
    }


def _pesos(turma):
    configuracao = _objeto(getattr(turma, "configuracao_simulacao", None))
    pesos = {}
    for criterio, padrao in PESOS_PADRAO.items():
        peso = _numero(configuracao.get(f"peso_{criterio}", padrao))
        pesos[criterio] = max(0.0, peso if peso is not None else padrao)
    total = sum(pesos.values())
    return {criterio: valor / total for criterio, valor in pesos.items()} if total else dict(PESOS_PADRAO)


def _normalizar_comparacao(valor, valores):
    if valor is None:
        return None
    minimo, maximo = min(valores), max(valores)
    # Empresas empatadas recebem o ponto neutro da escala comparativa.
    return 50.0 if maximo == minimo else 100.0 * (valor - minimo) / (maximo - minimo)


def gerar_relatorio(turma: Turma) -> dict:
    empresas = []
    for empresa in turma.empresas:
        decisoes = {d.rodada: d for d in empresa.decisoes}
        resultados = sorted(empresa.resultados, key=lambda r: r.rodada)
        rodadas = [_rodada(empresa, r, decisoes.get(r.rodada)) for r in resultados]
        ultimo = rodadas[-1] if rodadas else None
        patrimonio = None
        if ultimo:
            balanco = _objeto(ultimo["balanco"])
            patrimonio = _numero(balanco.get("patrimonio"))
            if patrimonio is None:
                patrimonio = resultados[-1].caixa_final - resultados[-1].divida_final
            else:
                final = _objeto(_objeto(ultimo["detalhes_simulacao"]).get("estado_final"))
                patrimonio -= _numero(final.get("capital_aportado")) or 0.0
        proporcoes = [r["participacao"]["proporcao_confirmada"] for r in rodadas]
        proporcoes = [v for v in proporcoes if v is not None]
        empresas.append({
            "id": empresa.id, "nome": empresa.nome, "membros": _membros(empresa),
            "resumo": {
                "rodadas_concluidas": len(rodadas),
                "receita_acumulada": round(sum(r.receita for r in resultados), 2),
                "lucro_acumulado": round(sum(r.lucro_liquido for r in resultados), 2),
                "patrimonio_sem_aportes": round(patrimonio, 2) if patrimonio is not None else None,
                "satisfacao": ultimo["indicadores"]["satisfacao"] if ultimo else None,
                "participacao": sum(proporcoes) / len(proporcoes) if proporcoes else None,
            },
            "rodadas": rodadas,
        })
    pesos = _pesos(turma)
    encerradas = [e for e in empresas if e["rodadas"]]
    comparacoes = {
        "lucro": [e["resumo"]["lucro_acumulado"] for e in encerradas],
        "patrimonio": [e["resumo"]["patrimonio_sem_aportes"] for e in encerradas],
    }
    ranking = []
    for empresa in empresas:
        resumo = empresa["resumo"]
        componentes = {criterio: None for criterio in PESOS_PADRAO}
        if empresa["rodadas"]:
            componentes["lucro"] = _normalizar_comparacao(resumo["lucro_acumulado"], comparacoes["lucro"])
            componentes["patrimonio"] = _normalizar_comparacao(resumo["patrimonio_sem_aportes"], comparacoes["patrimonio"])
            if resumo["satisfacao"] is not None:
                componentes["satisfacao"] = min(100.0, max(0.0, resumo["satisfacao"]))
            if resumo["participacao"] is not None:
                componentes["participacao"] = 100.0 * resumo["participacao"]
        peso_disponivel = sum(pesos[c] for c, v in componentes.items() if v is not None)
        pontuacao = sum(pesos[c] * v for c, v in componentes.items() if v is not None) / peso_disponivel if peso_disponivel else None
        ranking.append({
            "empresa_id": empresa["id"], "empresa": empresa["nome"],
            "pontuacao_didatica": round(pontuacao, 2) if pontuacao is not None else None,
            "nota_semestre": round(min(10.0, max(0.0, pontuacao / 10)), 2) if pontuacao is not None else None,
            "nota_provisoria": turma.rodada_atual <= turma.total_rodadas,
            "componentes": {c: round(v, 2) if v is not None else None for c, v in componentes.items()},
            **{chave: resumo[chave] for chave in ("lucro_acumulado", "patrimonio_sem_aportes", "satisfacao", "participacao")},
        })
    ranking.sort(key=lambda r: (r["pontuacao_didatica"] is None, -(r["pontuacao_didatica"] or 0.0), r["empresa_id"]))
    for posicao, linha in enumerate(ranking, 1):
        linha["posicao"] = posicao if linha["pontuacao_didatica"] is not None else None
    return {
        "turma": {
            "id": turma.id, "nome": turma.nome, "codigo": turma.codigo,
            "modo_jogo": getattr(turma, "modo_jogo", "LEGADO"),
            "rodada_atual": turma.rodada_atual, "total_rodadas": turma.total_rodadas,
        },
        "rubrica": {
            "tipo": "PONTUACAO_DIDATICA", "escala": [0, 100], "escala_nota": [0, 10], "formula_nota": "pontuacao_didatica / 10", "pesos": pesos,
            "criterios": {
                "lucro": "Lucro acumulado: comparação entre empresas, de 0 a 100; empate recebe 50.",
                "patrimonio": "Patrimônio do último encerramento menos aportes: comparação entre empresas; empate recebe 50.",
                "satisfacao": "Satisfação ao final da última rodada, de 0 a 100.",
                "participacao": "Média das confirmações da versão encerrada; no individual, proporção de entregas manuais.",
            },
            "observacao": "Pontuação didática comparativa, não é nota institucional. Critérios sem dados têm pesos redistribuídos. Login registra acesso, não comprova aprendizagem.",
        },
        "ranking": ranking, "empresas": empresas,
        "observacoes": [
            "Resultados anteriores são lidos como foram encerrados, sem recalcular o histórico.",
            "DFC, balanço e indicadores ausentes no motor legado permanecem sem dados.",
            "Capital de giro representa a necessidade operacional: estoques + contas a receber - contas a pagar.",
            "Margem, endividamento, ROE e churn são frações. Denominadores nulos ou negativos produzem indicador sem dados.",
            "Assinaturas anteriores permanecem no histórico; somente a versão encerrada conta como confirmação.",
        ],
    }


def _csv_numero(valor):
    return "" if valor is None else f"{valor:.6f}".rstrip("0").rstrip(".").replace(".", ",")


def _csv_texto(valor):
    texto = str(valor)
    return "'" + texto if texto.startswith(("=", "+", "-", "@", "\t", "\r")) else texto


def relatorio_csv(relatorio: dict) -> str:
    saida = io.StringIO(newline="")
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow([
        "Empresa", "Rodada", "Modo", "Pontuação didática (não é nota)", "Receita", "Lucro líquido",
        "Margem líquida", "Endividamento", "ROE", "Capital de giro", "Satisfação", "CAC", "LTV", "Churn", "Runway",
        "DRE", "DFC", "Balanço", "Operação", "Decisão", "Assinaturas", "Participação individual", "Alertas", "Rubrica", "Nota automática / 10", "Situação da nota", "Versão do motor",
    ])
    pontuacoes = {r["empresa_id"]: r["pontuacao_didatica"] for r in relatorio["ranking"]}
    codificar = lambda valor: json.dumps(valor, ensure_ascii=False, allow_nan=False) if valor is not None else ""
    for empresa in relatorio["empresas"]:
        for rodada in empresa["rodadas"]:
            indicadores = rodada["indicadores"]
            escritor.writerow([
                _csv_texto(empresa["nome"]), rodada["rodada"], rodada["modo"], _csv_numero(pontuacoes[empresa["id"]]),
                _csv_numero(rodada["dre"]["receita"]), _csv_numero(rodada["dre"]["lucro_liquido"]),
                *[_csv_numero(indicadores[k]) for k in ("margem_liquida", "endividamento", "roe", "capital_giro", "satisfacao", "cac", "ltv", "churn", "runway")],
                *[codificar(rodada[k]) for k in ("dre", "dfc", "balanco", "operacao", "decisao")],
                codificar(rodada["participacao"]["assinaturas"]), codificar(rodada["participacao"]),
                codificar(rodada["alertas"]), codificar(relatorio["rubrica"]),
                _csv_numero(next((r.get("nota_semestre") for r in relatorio["ranking"] if r["empresa_id"] == empresa["id"]), None)),
                "Provisória" if next((r.get("nota_provisoria", True) for r in relatorio["ranking"] if r["empresa_id"] == empresa["id"]), True) else "Final",
                rodada.get("engine_version", "1.0.0-legacy"),
            ])
    return "\ufeff" + saida.getvalue()
