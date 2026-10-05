from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import serializacao as ser
from ..database import get_db
from ..models import Decisao, Empresa, Resultado, StatusTurma, Turma, Usuario, agora
from ..motor.simulacao import perfil_inicial, prever_decisao
from ..schemas import DecisaoEntrada, EntrarTurmaEntrada
from ..seguranca import exigir_aluno

router = APIRouter(prefix="/api/aluno", tags=["aluno"])


def _empresa_do_aluno(db: Session, empresa_id: int, aluno: Usuario) -> Empresa:
    empresa = db.get(Empresa, empresa_id)
    if empresa is None or empresa.aluno_id != aluno.id:
        raise HTTPException(404, "Empresa não encontrada.")
    return empresa


@router.get("/empresas")
def minhas_empresas(db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno)):
    empresas = db.query(Empresa).filter(Empresa.aluno_id == aluno.id).order_by(Empresa.id.desc()).all()
    return [{"empresa": ser.empresa(e), "turma": ser.turma(e.turma)} for e in empresas]


@router.post("/turmas/entrar", status_code=201)
def entrar_na_turma(
    dados: EntrarTurmaEntrada, db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno)
):
    turma = db.query(Turma).filter(Turma.codigo == dados.codigo.strip().upper()).first()
    if turma is None:
        raise HTTPException(404, "Código de turma não encontrado. Confira com seu professor.")
    if turma.status != StatusTurma.ABERTA:
        raise HTTPException(422, "Esta turma já foi encerrada.")
    if turma.rodada_atual > 1:
        raise HTTPException(422, "A turma já começou. Peça ao professor para incluí-lo antes da 1ª rodada.")
    if db.query(Empresa).filter(Empresa.turma_id == turma.id, Empresa.aluno_id == aluno.id).first():
        raise HTTPException(409, "Você já tem uma empresa nesta turma.")

    perfil = perfil_inicial(dados.tipo_entrada_gem, dados.classe_dornelas)
    empresa = Empresa(
        turma_id=turma.id,
        aluno_id=aluno.id,
        nome=dados.nome_empresa.strip(),
        tipo_entrada_gem=dados.tipo_entrada_gem,
        classe_dornelas=dados.classe_dornelas,
        regime_tributario=dados.regime_tributario,
        caixa=turma.caixa_inicial,
        **perfil,
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return {"empresa": ser.empresa(empresa), "turma": ser.turma(turma)}


@router.get("/empresas/{empresa_id}")
def painel(empresa_id: int, db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno)):
    empresa = _empresa_do_aluno(db, empresa_id, aluno)
    turma = empresa.turma
    decisao_atual = (
        db.query(Decisao)
        .filter(Decisao.empresa_id == empresa.id, Decisao.rodada == turma.rodada_atual)
        .first()
    )
    ultima_decisao = (
        db.query(Decisao)
        .filter(Decisao.empresa_id == empresa.id)
        .order_by(Decisao.rodada.desc())
        .first()
    )

    # Informação de mercado da última rodada: preço médio e participação de cada concorrente
    ids = [e.id for e in turma.empresas]
    ultima_rodada = turma.rodada_atual - 1
    concorrentes = []
    if ultima_rodada >= 1:
        resultados = (
            db.query(Resultado)
            .filter(Resultado.rodada == ultima_rodada, Resultado.empresa_id.in_(ids))
            .all()
        )
        nomes = {e.id: e.nome for e in turma.empresas}
        concorrentes = sorted(
            (
                {
                    "empresa": nomes[r.empresa_id],
                    "propria": r.empresa_id == empresa.id,
                    "preco": r.preco,
                    "participacao_mercado": r.participacao_mercado,
                }
                for r in resultados
            ),
            key=lambda linha: linha["participacao_mercado"],
            reverse=True,
        )

    posicao = next(
        (linha["posicao"] for linha in ser.ranking(turma) if linha["empresa_id"] == empresa.id), None
    )

    return {
        "empresa": ser.empresa(empresa),
        "turma": ser.turma(turma, completa=True),
        "decisao_atual": ser.decisao(decisao_atual) if decisao_atual and not decisao_atual.automatica else None,
        "ultima_decisao": ser.decisao(ultima_decisao),
        "resultados": [ser.resultado(r) for r in empresa.resultados],
        "eventos": [ser.evento(e) for e in turma.eventos],
        "mercado": concorrentes,
        "posicao_ranking": posicao,
        "total_empresas": len(turma.empresas),
    }


def _validar_decisao(empresa: Empresa, dados: DecisaoEntrada) -> None:
    if empresa.turma.status != StatusTurma.ABERTA:
        raise HTTPException(422, "A turma foi encerrada; não há mais rodadas para decidir.")
    if dados.demitir > empresa.funcionarios:
        raise HTTPException(422, f"Você só pode demitir até {empresa.funcionarios} funcionário(s).")
    if dados.amortizacao > empresa.divida + dados.emprestimo + 0.01:
        raise HTTPException(422, "A amortização não pode ser maior que a dívida.")


@router.post("/empresas/{empresa_id}/previsao")
def previa_decisao(
    empresa_id: int,
    dados: DecisaoEntrada,
    db: Session = Depends(get_db),
    aluno: Usuario = Depends(exigir_aluno),
):
    empresa = _empresa_do_aluno(db, empresa_id, aluno)
    _validar_decisao(empresa, dados)
    return prever_decisao(empresa, Decisao(**dados.model_dump()), empresa.turma)


@router.put("/empresas/{empresa_id}/decisao")
def enviar_decisao(
    empresa_id: int,
    dados: DecisaoEntrada,
    db: Session = Depends(get_db),
    aluno: Usuario = Depends(exigir_aluno),
):
    empresa = _empresa_do_aluno(db, empresa_id, aluno)
    turma = empresa.turma
    _validar_decisao(empresa, dados)
    decisao = (
        db.query(Decisao)
        .filter(Decisao.empresa_id == empresa.id, Decisao.rodada == turma.rodada_atual)
        .first()
    )
    if decisao is None:
        decisao = Decisao(empresa_id=empresa.id, rodada=turma.rodada_atual)
        db.add(decisao)
    for campo, valor in dados.model_dump().items():
        setattr(decisao, campo, valor)
    decisao.automatica = 0
    decisao.enviada_em = agora()
    db.commit()
    db.refresh(decisao)
    return ser.decisao(decisao)
