from datetime import date, datetime, timedelta
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.prazos import limite_brasilia, validar_salvamento, vencido, fechar_vencidas
from app.database import SessionLocal
from app.models import Turma, Decisao, Resultado, agora
from .test_equipes import _criar_equipe, _salvar, _painel

def test_limite_exato_brasilia_sem_bloqueio_diario():
    limite = limite_brasilia(date(2026, 10, 9))
    assert limite == datetime(2026, 10, 10, 2, 59, 59)
    turma = SimpleNamespace(prazo_rodada=limite, prazo_numero_rodada=1, rodada_atual=1)
    validar_salvamento(turma, 1, limite-timedelta(seconds=1))
    validar_salvamento(turma, 1, limite-timedelta(days=1))
    with pytest.raises(HTTPException) as erro:
        validar_salvamento(turma, 1, limite)
    assert erro.value.status_code == 403
    assert vencido(turma, limite)
    turma.rodada_atual = 2
    assert not vencido(turma, limite)
    validar_salvamento(turma, 2, limite+timedelta(days=1))
    turma.prazo_rodada = None
    validar_salvamento(turma, 1, limite)

def test_fechamento_automatico_nao_duplica_e_preserva_rascunho(cliente, professor, monkeypatch):
    monkeypatch.setattr("app.routers.mercado.preparar_relatorios_automaticos", lambda *args: None)
    equipe = _criar_equipe(cliente, professor)
    _salvar(cliente, equipe, contratar=2)
    with SessionLocal() as db:
        turma = db.get(Turma, equipe["turma"]["id"])
        turma.prazo_rodada = agora()-timedelta(seconds=1)
        turma.prazo_numero_rodada = 1
        db.commit()
    resposta = cliente.put(f"/api/aluno/empresas/{equipe['id']}/decisao", headers=equipe["alunos"][0]["headers"], json={"preco":100,"rodada":1,"versao":1,"rascunho":True})
    assert resposta.status_code == 403
    fechar_vencidas(); fechar_vencidas()
    with SessionLocal() as db:
        turma = db.get(Turma, equipe["turma"]["id"])
        assert turma.rodada_atual == 2
        assert db.query(Resultado).count() == 1
        decisao = db.query(Decisao).filter_by(empresa_id=equipe["id"], rodada=1).one()
        assert decisao.contratar == 2 and decisao.automatica and decisao.enviada_em
    _salvar(cliente, equipe, preco=105)

def test_envio_final_imutavel_e_forcamento_manual(cliente, professor):
    equipe = _criar_equipe(cliente, professor)
    _salvar(cliente, equipe, rascunho=False)
    resposta = cliente.put(f"/api/aluno/empresas/{equipe['id']}/decisao", headers=equipe["alunos"][0]["headers"], json={"preco":80,"rodada":1,"versao":1,"rascunho":True})
    assert resposta.status_code == 403
    resposta = cliente.post(f"/api/professor/turmas/{equipe['turma']['id']}/fechar-rodada", headers=professor, json={"rodada":1,"forcar":True,"evento":"NENHUM"})
    assert resposta.status_code == 200
    _salvar(cliente, equipe)
