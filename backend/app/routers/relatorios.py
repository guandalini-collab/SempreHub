"""Acesso do professor aos relatórios de suas próprias turmas."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import AprovacaoDecisao, Decisao, Empresa, MembroEmpresa, RegistroEquipe, Turma, Usuario
from ..relatorios import gerar_relatorio, relatorio_csv
from ..seguranca import exigir_professor


router = APIRouter(prefix="/api/professor", tags=["relatorios"])


def _turma(db: Session, turma_id: int, professor: Usuario) -> Turma:
    # Filtrar pelo proprietário antes de carregar qualquer dado de alunos.
    turma = db.query(Turma).filter(Turma.id == turma_id, Turma.professor_id == professor.id).options(
        selectinload(Turma.empresas).selectinload(Empresa.aluno),
        selectinload(Turma.empresas).selectinload(Empresa.resultados),
        selectinload(Turma.empresas).selectinload(Empresa.decisoes).selectinload(Decisao.aprovacoes).selectinload(AprovacaoDecisao.aluno),
        selectinload(Turma.empresas).selectinload(Empresa.membros).selectinload(MembroEmpresa.aluno),
        selectinload(Turma.empresas).selectinload(Empresa.registros_equipe).selectinload(RegistroEquipe.aluno),
    ).first()
    if turma is None:
        raise HTTPException(404, "Turma não encontrada.")
    return turma


@router.get("/turmas/{turma_id}/relatorio")
def relatorio(
    turma_id: int,
    db: Session = Depends(get_db),
    professor: Usuario = Depends(exigir_professor),
):
    return gerar_relatorio(_turma(db, turma_id, professor))


@router.get("/turmas/{turma_id}/relatorio.csv")
def baixar_relatorio(
    turma_id: int,
    db: Session = Depends(get_db),
    professor: Usuario = Depends(exigir_professor),
):
    turma = _turma(db, turma_id, professor)
    conteudo = relatorio_csv(gerar_relatorio(turma))
    return StreamingResponse(
        iter([conteudo]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="semprehub_relatorio_{turma.codigo}.csv"'},
    )
