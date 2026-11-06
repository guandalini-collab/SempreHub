"""Consultas oficiais autenticadas para os dois perfis."""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..seguranca import exigir_professor, exigir_aluno
from ..models import ConteudoMercado, Usuario
from ..atualizacoes_oficiais import consultar, atualizar
from .professor import _turma_do_professor
from .aluno import _empresa_do_aluno

router=APIRouter(tags=['atualizacoes-oficiais'])


def _setor_atual(db, turma):
    edicao = (db.query(ConteudoMercado)
        .filter(ConteudoMercado.turma_id == turma.id, ConteudoMercado.publicado.is_(True), ConteudoMercado.rodada <= turma.rodada_atual)
        .order_by(ConteudoMercado.rodada.desc(), ConteudoMercado.id.desc()).first())
    return (edicao.dados or {}).get('setor') if edicao else None


@router.get('/api/professor/turmas/{turma_id}/atualizacoes-oficiais')
def docente(turma_id:int,tarefas:BackgroundTasks,db:Session=Depends(get_db),usuario:Usuario=Depends(exigir_professor)):
    turma = _turma_do_professor(db,turma_id,usuario)
    dados=consultar(db, _setor_atual(db, turma))
    if dados['consulta_vencida']: tarefas.add_task(atualizar)
    return dados


@router.get('/api/aluno/empresas/{empresa_id}/atualizacoes-oficiais')
def discente(empresa_id:int,tarefas:BackgroundTasks,db:Session=Depends(get_db),usuario:Usuario=Depends(exigir_aluno)):
    empresa = _empresa_do_aluno(db,empresa_id,usuario)
    dados=consultar(db, _setor_atual(db, empresa.turma))
    if dados['consulta_vencida']: tarefas.add_task(atualizar)
    return dados
