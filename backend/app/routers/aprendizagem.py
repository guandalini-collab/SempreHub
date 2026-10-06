"""Devolutiva e notícias baseadas nas rodadas preservadas da empresa."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..educacao import listar_midias, obter_ressalvas
from ..models import Usuario
from ..relatorios import _rodada
from ..seguranca import exigir_aluno
from .aluno import _empresa_do_aluno

router = APIRouter(prefix="/api/aluno/empresas", tags=["aprendizagem"])


@router.get("/{empresa_id}/relatorio-primeira-rodada")
def primeira_rodada(empresa_id: int, db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno)):
    empresa = _empresa_do_aluno(db, empresa_id, aluno)
    resultado = next((r for r in empresa.resultados if r.rodada == 1), None)
    if resultado is None:
        raise HTTPException(409, "O relatório ficará disponível após o fechamento da primeira rodada pelo sistema.")
    decisao = next((d for d in empresa.decisoes if d.rodada == 1), None)
    evento = next((e for e in empresa.turma.eventos if e.rodada == 1), None)
    dados_resultado = _rodada(empresa, resultado, decisao)
    dados_resultado.update(caixa_final=resultado.caixa_final, divida_final=resultado.divida_final)
    return {
        "empresa": empresa.nome, "turma": empresa.turma.nome,
        "resultado": dados_resultado,
        "evento": {"titulo": evento.titulo, "narrativa": evento.narrativa} if evento else None,
        "perguntas": [
            "Como preço, capacidade e investimentos se relacionaram com as vendas?",
            "O lucro gerado se transformou em caixa? Examine os prazos de recebimento e pagamento.",
            "Quais forças, fraquezas, oportunidades e ameaças os dados revelaram?",
            "Que hipótese a equipe pretende testar na próxima rodada?",
        ],
        "midias": listar_midias(), "ressalvas": obter_ressalvas(),
    }


@router.get("/{empresa_id}/news")
def news(empresa_id: int, db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno)):
    empresa = _empresa_do_aluno(db, empresa_id, aluno)
    turma = empresa.turma
    edicoes = []
    for evento in sorted(turma.eventos, key=lambda e: e.rodada, reverse=True):
        resultados = [r for e in turma.empresas for r in e.resultados if r.rodada == evento.rodada]
        edicoes.append({
            "rodada": evento.rodada, "titulo": evento.titulo, "narrativa": evento.narrativa,
            "mercado": {
                "preco_medio": sum(r.preco for r in resultados) / len(resultados),
                "unidades_vendidas": sum(r.unidades_vendidas for r in resultados),
                "receita_total": sum(r.receita for r in resultados),
            } if resultados else None,
        })
    return {"jornal": "SempreHub News", "rodada_atual": turma.rodada_atual, "edicoes": edicoes,
            "orientacao": "Relacione os eventos e os indicadores de mercado com os resultados da sua empresa. As condições de mercado são aplicadas pelo sistema no fechamento."}
