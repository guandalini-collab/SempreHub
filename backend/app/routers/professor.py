import csv
import io
import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import serializacao as ser
from ..database import get_db
from ..models import Decisao, Empresa, Resultado, StatusTurma, Turma, Usuario
from ..motor.eventos import opcoes_evento
from ..motor.simulacao import processar_rodada
from ..schemas import FecharRodadaEntrada, ParametrosTurma, TurmaEntrada
from ..seguranca import exigir_professor

router = APIRouter(prefix="/api/professor", tags=["professor"])

_ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O e 1/I para evitar confusão


def _gerar_codigo(db: Session) -> str:
    while True:
        codigo = "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(6))
        if not db.query(Turma).filter(Turma.codigo == codigo).first():
            return codigo


def _turma_do_professor(db: Session, turma_id: int, professor: Usuario) -> Turma:
    turma = db.get(Turma, turma_id)
    if turma is None or turma.professor_id != professor.id:
        raise HTTPException(404, "Turma não encontrada.")
    return turma


@router.get("/eventos")
def listar_eventos(_: Usuario = Depends(exigir_professor)):
    return opcoes_evento()


@router.get("/turmas")
def listar_turmas(db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    turmas = db.query(Turma).filter(Turma.professor_id == professor.id).order_by(Turma.id.desc()).all()
    return [ser.turma(t) for t in turmas]


@router.post("/turmas", status_code=201)
def criar_turma(
    dados: TurmaEntrada, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)
):
    turma = Turma(professor_id=professor.id, codigo=_gerar_codigo(db), **dados.model_dump())
    db.add(turma)
    db.commit()
    db.refresh(turma)
    return ser.turma(turma, completa=True)


@router.put("/turmas/{turma_id}/parametros")
def atualizar_parametros(
    turma_id: int,
    dados: ParametrosTurma,
    db: Session = Depends(get_db),
    professor: Usuario = Depends(exigir_professor),
):
    turma = _turma_do_professor(db, turma_id, professor)
    if turma.rodada_atual > 1:
        # Depois da 1ª rodada só o número total de rodadas pode mudar, para não distorcer a competição
        if dados.total_rodadas < turma.rodada_atual - 1:
            raise HTTPException(422, "O total de rodadas não pode ser menor que as rodadas já jogadas.")
        turma.total_rodadas = dados.total_rodadas
        if turma.rodada_atual <= turma.total_rodadas:
            turma.status = StatusTurma.ABERTA
    else:
        caixa_anterior = turma.caixa_inicial
        for campo, valor in dados.model_dump().items():
            setattr(turma, campo, valor)
        for empresa in turma.empresas:
            if empresa.caixa == caixa_anterior:
                empresa.caixa = turma.caixa_inicial
    db.commit()
    db.refresh(turma)
    return ser.turma(turma, completa=True)


@router.get("/turmas/{turma_id}")
def detalhar_turma(
    turma_id: int, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)
):
    turma = _turma_do_professor(db, turma_id, professor)
    enviadas = {
        d.empresa_id
        for d in db.query(Decisao).filter(
            Decisao.rodada == turma.rodada_atual,
            Decisao.automatica == 0,
            Decisao.empresa_id.in_([e.id for e in turma.empresas] or [0]),
        )
    }
    empresas = []
    for e in turma.empresas:
        dados = ser.empresa(e)
        dados["decisao_enviada"] = e.id in enviadas
        empresas.append(dados)
    return {
        "turma": ser.turma(turma, completa=True),
        "empresas": empresas,
        "ranking": ser.ranking(turma),
        "eventos": [ser.evento(ev) for ev in turma.eventos],
        "mercado": _resumo_mercado(db, turma),
    }


def _resumo_mercado(db: Session, turma: Turma):
    ids = [e.id for e in turma.empresas] or [0]
    resumo = []
    for rodada in range(1, turma.rodada_atual):
        resultados = (
            db.query(Resultado).filter(Resultado.rodada == rodada, Resultado.empresa_id.in_(ids)).all()
        )
        if not resultados:
            continue
        resumo.append(
            {
                "rodada": rodada,
                "preco_medio": sum(r.preco for r in resultados) / len(resultados),
                "unidades": sum(r.unidades_vendidas for r in resultados),
                "receita": sum(r.receita for r in resultados),
                "lucro": sum(r.lucro_liquido for r in resultados),
            }
        )
    return resumo


@router.get("/turmas/{turma_id}/empresas/{empresa_id}")
def detalhar_empresa(
    turma_id: int,
    empresa_id: int,
    db: Session = Depends(get_db),
    professor: Usuario = Depends(exigir_professor),
):
    turma = _turma_do_professor(db, turma_id, professor)
    empresa = db.get(Empresa, empresa_id)
    if empresa is None or empresa.turma_id != turma.id:
        raise HTTPException(404, "Empresa não encontrada nesta turma.")
    decisoes = {d.rodada: ser.decisao(d) for d in empresa.decisoes}
    return {
        "empresa": ser.empresa(empresa),
        "resultados": [ser.resultado(r) for r in empresa.resultados],
        "decisoes": [decisoes[r] for r in sorted(decisoes)],
    }


@router.post("/turmas/{turma_id}/fechar-rodada")
def fechar_rodada(
    turma_id: int,
    dados: FecharRodadaEntrada,
    db: Session = Depends(get_db),
    professor: Usuario = Depends(exigir_professor),
):
    turma = _turma_do_professor(db, turma_id, professor)
    try:
        evento = processar_rodada(db, turma, dados.evento)
    except ValueError as erro:
        db.rollback()
        raise HTTPException(422, str(erro))
    db.refresh(turma)
    return {"evento": ser.evento(evento), "turma": ser.turma(turma, completa=True)}


@router.get("/turmas/{turma_id}/exportar.csv")
def exportar_csv(
    turma_id: int, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)
):
    turma = _turma_do_professor(db, turma_id, professor)
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    cabecalho = [
        "rodada", "empresa", "aluno", "email", "regime", "preco", "unidades_vendidas",
        "participacao_mercado", "receita", "impostos", "cmv", "folha", "custos_fixos",
        "marketing", "pd", "networking", "rescisoes", "royalties", "juros", "multas",
        "lucro_liquido", "caixa_final", "divida_final", "funcionarios", "fase",
        "autoeficacia", "networking_indice", "necessidade_realizacao",
    ]
    escritor.writerow(cabecalho)
    for e in turma.empresas:
        for r in e.resultados:
            escritor.writerow(
                [
                    r.rodada, e.nome, e.aluno.nome, e.aluno.email, r.regime.value,
                    _br(r.preco), _br(r.unidades_vendidas), _br(r.participacao_mercado),
                    _br(r.receita), _br(r.impostos), _br(r.cmv), _br(r.folha), _br(r.custos_fixos),
                    _br(r.marketing), _br(r.pd), _br(r.networking_invest), _br(r.rescisoes),
                    _br(r.royalties), _br(r.juros), _br(r.multas), _br(r.lucro_liquido),
                    _br(r.caixa_final), _br(r.divida_final), r.funcionarios, r.fase.value,
                    _br(r.autoeficacia), _br(r.networking), _br(r.necessidade_realizacao),
                ]
            )
    conteudo = "﻿" + saida.getvalue()  # BOM para o Excel reconhecer acentos
    nome_arquivo = f"semprehub_{turma.codigo}.csv"
    return StreamingResponse(
        iter([conteudo]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


def _br(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")
