"""Pesquisa automática de mercado antes da abertura da rodada."""
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app import pesquisa_automatica as auto
from app.database import SessionLocal
from app.evidencias_mercado import Documento
from app.models import ConteudoMercado, EventoRodada, PesquisaAutomatica, Turma

from .conftest import cadastrar
from .decisoes import completar_decisao
from .test_fluxo import _criar_turma, _entrar
from .test_mercado import edicao

ABERTURA = datetime(2026, 11, 20, 22, 0)  # 19h de Brasília


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "somente-teste")
    monkeypatch.setattr("app.evidencias_mercado.obter_documento", lambda url: Documento(
        '<meta property="article:published_time" content="2026-10-06"><main>Produto de teste R$ 30,00 por unidade ou cliente/mês.</main>'))


def _gerar_ok(monkeypatch, chamadas=None):
    from app.routers import mercado
    def gerar(*a):
        if chamadas is not None: chamadas.append(a[7] if len(a) > 7 else 1)
        return edicao(), {"https://www.ibge.gov.br/produto"}
    monkeypatch.setattr(mercado, "gerar_json", gerar)


def _turma_com_agenda(cliente, professor, setor="Pet Shop", modo_jogo="LEGADO"):
    turma = _criar_turma(cliente, professor, total_rodadas=3, modo_jogo=modo_jogo)
    with SessionLocal() as db:
        t = db.get(Turma, turma["id"])
        t.agenda_academica = {"rodadas": [
            {"rodada": 1, "abre_em": (ABERTURA - timedelta(days=7)).isoformat() + "Z", "fecha_em": ABERTURA.isoformat() + "Z"},
            {"rodada": 2, "abre_em": ABERTURA.isoformat() + "Z", "fecha_em": (ABERTURA + timedelta(days=7)).isoformat() + "Z"}]}
        t.prazo_rodada, t.prazo_numero_rodada = ABERTURA, 1
        if setor:
            t.configuracao_simulacao = {**(t.configuracao_simulacao or {}), "setor_mercado": setor}
        db.commit()
    return turma["id"]


def _registro(turma_id, rodada):
    with SessionLocal() as db:
        r = db.query(PesquisaAutomatica).filter_by(turma_id=turma_id, rodada=rodada).first()
        return None if r is None else (r.situacao, r.tentativas, r.mensagem, r.conteudo_id)


def _abrir_rodada_2(turma_id):
    with SessionLocal() as db:
        t = db.get(Turma, turma_id)
        t.rodada_atual, t.abertura_rodada = 2, ABERTURA
        t.prazo_rodada, t.prazo_numero_rodada = ABERTURA + timedelta(days=7), 2
        db.commit()


def test_com_agenda_pesquisa_2h_antes_e_publica_na_abertura(cliente, professor, monkeypatch):
    _gerar_ok(monkeypatch)
    turma_id = _turma_com_agenda(cliente, professor)
    auto.executar_ciclo(ABERTURA - timedelta(hours=3))
    assert _registro(turma_id, 2) is None
    auto.executar_ciclo(ABERTURA - timedelta(hours=2))
    situacao, tentativas, _, conteudo_id = _registro(turma_id, 2)
    assert (situacao, tentativas) == ("PRONTA", 1)
    with SessionLocal() as db:
        e = db.get(ConteudoMercado, conteudo_id)
        assert e.rodada == 2 and not e.publicado
    # Antes da abertura, nada é publicado; o professor ainda pode revisar.
    auto.executar_ciclo(ABERTURA - timedelta(minutes=10))
    assert _registro(turma_id, 2)[0] == "PRONTA"
    _abrir_rodada_2(turma_id)
    auto.executar_ciclo(ABERTURA + timedelta(minutes=1))
    assert _registro(turma_id, 2)[0] == "PUBLICADA"
    with SessionLocal() as db:
        assert db.get(ConteudoMercado, conteudo_id).publicado
    painel = cliente.get(f"/api/professor/turmas/{turma_id}/mercado", headers=professor).json()["pesquisa_automatica"]
    assert painel["com_agenda"] and painel["registros"][0]["situacao"] == "PUBLICADA"


def test_ate_tres_tentativas_e_nenhuma_depois_de_30_min_antes(cliente, professor, monkeypatch):
    from app.routers import mercado
    def falhar(*a): raise HTTPException(502, "A pesquisa não respondeu. Tente novamente.")
    monkeypatch.setattr(mercado, "gerar_json", falhar)
    # Startup: sem catálogo fixo, nada conferido não gera edição. Nos modos com
    # catálogo, a edição sai com o catálogo e o aviso de notícias faltantes.
    turma_id = _turma_com_agenda(cliente, professor, modo_jogo="STARTUP")
    auto.executar_ciclo(ABERTURA - timedelta(minutes=120))
    assert _registro(turma_id, 2)[:2] == ("FALHOU", 1)
    auto.executar_ciclo(ABERTURA - timedelta(minutes=100))
    assert _registro(turma_id, 2)[1] == 1  # aguarda o intervalo
    auto.executar_ciclo(ABERTURA - timedelta(minutes=90))
    auto.executar_ciclo(ABERTURA - timedelta(minutes=60))
    assert _registro(turma_id, 2)[1] == 3
    auto.executar_ciclo(ABERTURA - timedelta(minutes=30))
    auto.executar_ciclo(ABERTURA - timedelta(minutes=29))
    situacao, tentativas, mensagem, _ = _registro(turma_id, 2)
    assert (situacao, tentativas) == ("FALHOU", 3) and "Nenhum item" in mensagem


def test_ultima_tentativa_respeita_30_minutos(cliente, professor, monkeypatch):
    chamadas = []
    _gerar_ok(monkeypatch, chamadas)
    turma_id = _turma_com_agenda(cliente, professor)
    auto.executar_ciclo(ABERTURA - timedelta(minutes=29))
    assert _registro(turma_id, 2) is None and chamadas == []


def test_edicao_do_professor_nunca_e_publicada_pela_automacao(cliente, professor, monkeypatch):
    _gerar_ok(monkeypatch)
    turma_id = _turma_com_agenda(cliente, professor)
    with SessionLocal() as db:
        db.add(ConteudoMercado(turma_id=turma_id, rodada=2, dados=edicao()))
        db.commit()
    auto.executar_ciclo(ABERTURA - timedelta(hours=2))
    assert _registro(turma_id, 2)[0] == "IGNORADA"
    _abrir_rodada_2(turma_id)
    auto.executar_ciclo(ABERTURA + timedelta(minutes=1))
    with SessionLocal() as db:
        assert not db.query(ConteudoMercado).filter_by(turma_id=turma_id, publicado=True).first()


def test_sem_setor_pede_primeira_pesquisa_manual(cliente, professor, monkeypatch):
    chamadas = []
    _gerar_ok(monkeypatch, chamadas)
    turma_id = _turma_com_agenda(cliente, professor, setor=None)
    auto.executar_ciclo(ABERTURA - timedelta(hours=2))
    situacao, _, mensagem, _ = _registro(turma_id, 2)
    assert situacao == "IGNORADA" and "primeira pesquisa" in mensagem and chamadas == []


def test_tentativa_interrompida_e_repetida(cliente, professor, monkeypatch):
    _gerar_ok(monkeypatch)
    turma_id = _turma_com_agenda(cliente, professor)
    with SessionLocal() as db:
        db.add(PesquisaAutomatica(turma_id=turma_id, rodada=2, situacao="EM_ANDAMENTO", tentativas=1,
                                  atualizado_em=ABERTURA - timedelta(minutes=120)))
        db.commit()
    auto.executar_ciclo(ABERTURA - timedelta(minutes=110))
    assert _registro(turma_id, 2)[0] == "EM_ANDAMENTO"  # ainda dentro do tempo máximo
    auto.executar_ciclo(ABERTURA - timedelta(minutes=100))
    assert _registro(turma_id, 2)[:2] == ("PRONTA", 2)


def test_sem_agenda_pesquisa_e_publica_logo_apos_o_fechamento(cliente, professor, monkeypatch):
    _gerar_ok(monkeypatch)
    turma = _criar_turma(cliente, professor, total_rodadas=3)
    turma_id = turma["id"]
    auto.executar_ciclo()
    assert _registro(turma_id, 1) is None  # primeira rodada fica com o professor
    with SessionLocal() as db:
        t = db.get(Turma, turma_id)
        t.configuracao_simulacao = {**(t.configuracao_simulacao or {}), "setor_mercado": "Pet Shop"}
        db.commit()
    aluno = cadastrar(cliente, "Ana", "ana-auto@aluno.iffar.edu.br")
    empresa = _entrar(cliente, aluno, turma["codigo"], "Empresa Ana")
    assert cliente.put(f"/api/aluno/empresas/{empresa}/decisao", headers=aluno, json=completar_decisao({"preco": 60})).status_code == 200
    r = cliente.post(f"/api/professor/turmas/{turma_id}/fechar-rodada", headers=professor, json={"evento": "NENHUM"})
    assert r.status_code == 200, r.text
    auto.executar_ciclo()
    assert _registro(turma_id, 2)[0] == "PUBLICADA"
    with SessionLocal() as db:
        assert db.query(ConteudoMercado).filter_by(turma_id=turma_id, rodada=2, publicado=True).one()
        fechamento = db.query(EventoRodada).filter_by(turma_id=turma_id, rodada=1).one()
        instante_tardio = fechamento.criado_em + timedelta(hours=7)
    # Fora da janela após o fechamento, nada roda (protege turmas antigas).
    with SessionLocal() as db:
        db.query(PesquisaAutomatica).delete(); db.query(ConteudoMercado).delete(); db.commit()
    auto.executar_ciclo(instante_tardio)
    assert _registro(turma_id, 2) is None


def test_sem_credencial_nada_roda(cliente, professor, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("SEMPREHUB_OPENAI_API_KEY", "")
    turma_id = _turma_com_agenda(cliente, professor)
    auto.executar_ciclo(ABERTURA - timedelta(hours=2))
    assert _registro(turma_id, 2) is None
