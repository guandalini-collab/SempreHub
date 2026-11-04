"""Consultas oficiais autenticadas para os dois perfis."""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..seguranca import exigir_professor, exigir_aluno
from ..models import Usuario
from ..atualizacoes_oficiais import consultar, atualizar
from .professor import _turma_do_professor
from .aluno import _empresa_do_aluno

router=APIRouter(tags=['atualizacoes-oficiais'])


@router.get('/api/professor/turmas/{turma_id}/atualizacoes-oficiais')
def docente(turma_id:int,tarefas:BackgroundTasks,db:Session=Depends(get_db),usuario:Usuario=Depends(exigir_professor)):
    _turma_do_professor(db,turma_id,usuario)
    dados=consultar(db)
    if dados['consulta_vencida']: tarefas.add_task(atualizar)
    return dados


@router.get('/api/aluno/empresas/{empresa_id}/atualizacoes-oficiais')
def discente(empresa_id:int,tarefas:BackgroundTasks,db:Session=Depends(get_db),usuario:Usuario=Depends(exigir_aluno)):
    _empresa_do_aluno(db,empresa_id,usuario)
    dados=consultar(db)
    if dados['consulta_vencida']: tarefas.add_task(atualizar)
    return dados
