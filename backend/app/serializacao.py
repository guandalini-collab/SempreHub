"""Conversão dos modelos em dicionários enviados ao navegador."""

from typing import Any, Dict, List, Optional

from .models import Decisao, Empresa, EventoRodada, Resultado, Turma, Usuario
from .motor.tributos import FATOR_CLT

CAMPOS_PARAMETROS = [
    "modo_equipe",
    "modo_jogo", "cenario", "configuracao_simulacao",
    "total_rodadas",
    "caixa_inicial",
    "preco_referencia",
    "custo_unitario",
    "demanda_base_por_empresa",
    "crescimento_mercado_mensal",
    "produtividade_por_pessoa",
    "custos_fixos_mensais",
    "salario_base",
    "taxa_juros_mensal",
    "taxa_cheque_especial",
    "limite_credito",
    "probabilidade_evento",
    "teto_mei_anual",
    "das_mei_mensal",
    "aliquota_icms",
]


def usuario(u: Usuario) -> Dict[str, Any]:
    return {
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "papel": u.papel.value,
        "teste": u.criado_por_id is not None,
    }


def turma(t: Turma, completa: bool = False) -> Dict[str, Any]:
    dados = {
        "id": t.id,
        "nome": t.nome,
        "codigo": t.codigo,
        "status": t.status.value,
        "rodada_atual": t.rodada_atual,
        "total_rodadas": t.total_rodadas,
        "modo_equipe": t.modo_equipe,
        "modo_jogo": t.modo_jogo,
        "cenario": t.cenario,
        "versao_motor": t.versao_motor,
        "professor": t.professor.nome if t.professor else None,
        "quantidade_empresas": len(t.empresas),
    }
    if completa:
        dados["parametros"] = {campo: getattr(t, campo) for campo in CAMPOS_PARAMETROS}
        from .motor.avancado import config
        dados["parametros"]["configuracao_simulacao"] = config(t)
        dados["greve_rodadas_restantes"] = t.cmv_rodadas_restantes
    return dados


def decisao(d: Optional[Decisao]) -> Optional[Dict[str, Any]]:
    if d is None:
        return None
    return {
        "rodada": d.rodada,
        "versao": d.versao,
        "simulacao": d.simulacao,
        "preco": d.preco,
        "marketing": d.marketing,
        "pd": d.pd,
        "networking": d.networking,
        "contratar": d.contratar,
        "demitir": d.demitir,
        "emprestimo": d.emprestimo,
        "amortizacao": d.amortizacao,
        "regime_solicitado": d.regime_solicitado.value if d.regime_solicitado else None,
        "automatica": bool(d.automatica),
        "enviada_em": d.enviada_em.isoformat() + "Z" if d.enviada_em else None,
        "aprovacoes": [
            {
                "aluno_id": a.aluno_id, "nome": a.aluno.nome,
                "versao": a.versao, "aprovado_em": a.aprovado_em.isoformat() + "Z",
                "conteudo": a.conteudo,
            }
            for a in d.aprovacoes
        ],
    }


def resultado(r: Resultado) -> Dict[str, Any]:
    dados = {
        "detalhes_simulacao": r.detalhes_simulacao,
        "rodada": r.rodada,
        "preco": r.preco,
        "demanda": r.demanda,
        "capacidade": r.capacidade,
        "unidades_vendidas": r.unidades_vendidas,
        "participacao_mercado": r.participacao_mercado,
        "dre": {
            "receita": r.receita,
            "impostos": r.impostos,
            "cmv": r.cmv,
            "folha": r.folha,
            "custos_fixos": r.custos_fixos,
            "marketing": r.marketing,
            "pd": r.pd,
            "networking": r.networking_invest,
            "rescisoes": r.rescisoes,
            "royalties": r.royalties,
            "juros": r.juros,
            "multas": r.multas,
            "lucro_liquido": r.lucro_liquido,
        },
        "caixa_final": r.caixa_final,
        "divida_final": r.divida_final,
        "regime": r.regime.value,
        "aliquota_efetiva": r.aliquota_efetiva,
        "funcionarios": r.funcionarios,
        "marca": r.marca,
        "qualidade": r.qualidade,
        "autoeficacia": r.autoeficacia,
        "networking": r.networking,
        "necessidade_realizacao": r.necessidade_realizacao,
        "fase": r.fase.value,
        "alertas": r.alertas or [],
    }
    if r.detalhes_simulacao:
        extras = r.detalhes_simulacao.get("dre", {})
        for campo in ("refugos", "frete", "armazenagem", "depreciacao", "beneficios", "treinamento", "manutencao"):
            dados["dre"][campo] = extras.get(campo, 0)
    return dados


def evento(e: EventoRodada) -> Dict[str, Any]:
    return {"rodada": e.rodada, "codigo": e.codigo, "titulo": e.titulo, "narrativa": e.narrativa}


def empresa(e: Empresa) -> Dict[str, Any]:
    from .motor.avancado import patrimonio
    dados = {
        "id": e.id,
        "nome": e.nome,
        "aluno": e.aluno.nome if e.aluno else None,
        "aluno_id": e.aluno_id,
        "aluno_email": e.aluno.email if e.aluno else None,
        "tipo_entrada_gem": e.tipo_entrada_gem.value,
        "classe_dornelas": e.classe_dornelas.value,
        "regime_tributario": e.regime_tributario.value,
        "regime_pretendido": e.regime_pretendido.value if e.regime_pretendido else None,
        "fase_atual": e.fase_atual.value,
        "caixa": e.caixa,
        "divida": e.divida,
        "patrimonio": patrimonio(e),
        "estado_simulacao": e.estado_simulacao,
        "funcionarios": e.funcionarios,
        "marca": e.marca,
        "qualidade": e.qualidade,
        "autoeficacia": e.autoeficacia,
        "necessidade_realizacao": e.necessidade_realizacao,
        "networking": e.networking,
        "faturamento_ano": e.faturamento_ano,
        "fator_clt": FATOR_CLT[e.regime_tributario],
    }
    if e.turma.modo_equipe:
        dados["equipe_membros"] = [
            {"aluno_id": m.aluno_id, "nome": m.aluno.nome, "cargos": m.cargos or []}
            for m in e.membros
        ]
    return dados


def ranking(t: Turma) -> List[Dict[str, Any]]:
    from .motor.avancado import patrimonio
    linhas = []
    for e in t.empresas:
        lucro_acumulado = sum(r.lucro_liquido for r in e.resultados)
        ultimo = e.resultados[-1] if e.resultados else None
        linhas.append(
            {
                "empresa_id": e.id,
                "empresa": e.nome,
                "aluno": e.aluno.nome if e.aluno else None,
                "patrimonio": patrimonio(e),
                "patrimonio_sem_aportes": patrimonio(e) - (e.estado_simulacao or {}).get("capital_aportado", 0),
                "caixa": e.caixa,
                "divida": e.divida,
                "lucro_acumulado": lucro_acumulado,
                "participacao_mercado": ultimo.participacao_mercado if ultimo else 0.0,
                "preco": ultimo.preco if ultimo else None,
                "fase": e.fase_atual.value,
            }
        )
    linhas.sort(key=lambda linha: linha["patrimonio_sem_aportes"], reverse=True)
    for posicao, linha in enumerate(linhas, start=1):
        linha["posicao"] = posicao
    return linhas
