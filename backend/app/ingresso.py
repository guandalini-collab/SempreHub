"""Vínculo com uma turma e sala de formação por afinidade."""
from fastapi import HTTPException
from sqlalchemy import update
from .models import Empresa, MatriculaTurma, MembroEmpresa, StatusTurma, Turma, Usuario, agora
from .equipes import bloquear_turma


def matricular(db, aluno, turma_id):
    # Bloqueia a conta antes de ler o vínculo: ingressos concorrentes em turmas distintas
    # não podem ultrapassar a trava, inclusive em SQLite.
    db.execute(update(Usuario).where(Usuario.id == aluno.id).values(versao_sessao=Usuario.versao_sessao), execution_options={"synchronize_session": False})
    m = db.query(MatriculaTurma).filter_by(aluno_id=aluno.id).populate_existing().first()
    # Trocas e fechamento usam os mesmos bloqueios, em ordem estável.
    turmas = {tid: bloquear_turma(db, tid) for tid in sorted({turma_id, *([m.turma_id] if m else [])})}
    turma = turmas[turma_id]
    if m and m.turma_id == turma.id:
        return turma
    if m and m.autorizada_turma_id != turma.id:
        raise HTTPException(403, "Você já está vinculado a outra turma. A troca exige autorização do professor.")
    if not turma.visivel_ingresso or turma.formacao_encerrada or turma.status != StatusTurma.ABERTA or turma.rodada_atual != 1:
        raise HTTPException(422, "Esta turma não está disponível para ingresso. Procure o professor.")
    if not m:
        anterior = db.query(Empresa).filter_by(aluno_id=aluno.id).first() or db.query(MembroEmpresa).filter_by(aluno_id=aluno.id).first()
        if anterior and anterior.turma_id != turma.id:
            raise HTTPException(403, "A troca de turma exige autorização do professor.")
        m = MatriculaTurma(aluno_id=aluno.id, turma_id=turma.id, historico=[])
        db.add(m)
    else:
        m.historico = [*(m.historico or []), {"acao": "TROCAR_TURMA", "origem": m.turma_id, "destino": turma.id, "data": agora().isoformat()}]
        anterior_id = m.turma_id
        membro = db.query(MembroEmpresa).filter_by(turma_id=anterior_id, aluno_id=aluno.id).first()
        if membro:
            from .equipes import invalidar_aprovacoes, registrar
            empresa = membro.empresa
            registrar(db, empresa, aluno, "SAIR_POR_TROCA_TURMA", invalidar_aprovacoes(db, empresa), {"destino": turma.id})
            db.delete(membro)
        m.turma_id = turma.id
        m.autorizada_turma_id = None
    db.flush()
    return turma


def sala(db, turma):
    inscritos = db.query(MatriculaTurma).filter_by(turma_id=turma.id).all()
    ocupados = {e.aluno_id for e in turma.empresas} | {m.aluno_id for e in turma.empresas for m in e.membros}
    return {"turma_id": turma.id, "formacao_encerrada": turma.formacao_encerrada,
        "disponiveis": [{"aluno_id": m.aluno_id, "nome": m.aluno.nome} for m in inscritos if m.aluno_id not in ocupados],
        "equipes": [{"empresa_id": e.id, "nome": e.nome,
            "membros": [{"aluno_id": m.aluno_id, "nome": m.aluno.nome} for m in e.membros],
            "vagas": max(0, 5-len(e.membros)), "completa": len(e.membros) == 5} for e in turma.empresas]}
