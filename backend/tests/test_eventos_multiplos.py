import random

import pytest

from app.motor import eventos
from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar


def test_sorteio_varia_quantidade_e_evitar_eventos_opostos():
    quantidades = set()
    observados = set()
    for seed in range(100):
        evento = eventos.escolher_evento("SORTEAR", 1, random.Random(seed))
        codigos = set(evento.codigos or (evento.codigo,))
        quantidades.add(len(codigos))
        observados.update(codigos)
        assert not {"ALTA_SELIC", "QUEDA_SELIC"}.issubset(codigos)
        assert not {"DEMANDA_AQUECIDA", "RETRACAO_ECONOMICA"}.issubset(codigos)
        assert len(evento.codigo) <= 40
        assert len(evento.titulo) <= 120
        assert len(evento.narrativa) <= 1000
    assert quantidades == {1, 2, 3}
    assert observados == set(eventos.EVENTOS)
    assert eventos.escolher_evento("SORTEAR", 0, random.Random(1)) == eventos.NENHUM


@pytest.mark.parametrize("modo", ["LEGADO", "TRADICIONAL"])
def test_aplica_todos_os_efeitos_e_registra_historico(cliente, professor, monkeypatch, modo):
    turma = _criar_turma(cliente, professor, modo_jogo=modo)
    aluno = cadastrar(cliente, "Ana", "multiplos@aluno.iffar.edu.br")
    empresa = _entrar(cliente, aluno, turma["codigo"], "Teste", classe="FRANQUIA")
    codigos = ("ALTA_SELIC", "GREVE_LOGISTICA", "NOTIFICACAO_FISCAL")
    conjunto = eventos.Evento("MULTIPLOS", "Três eventos", "Juros, logística e fiscalização.", codigos)
    monkeypatch.setattr(eventos, "escolher_evento", lambda *args: conjunto)
    r = cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "SORTEAR", "rodada": 1})
    assert r.status_code == 200, r.text
    assert r.json()["evento"]["codigo"] == "MULTIPLOS"
    assert r.json()["evento"]["narrativa"] == conjunto.narrativa
    assert r.json()["turma"]["parametros"]["taxa_juros_mensal"] == pytest.approx(.03)
    assert r.json()["turma"]["greve_rodadas_restantes"] == 1
    detalhe = cliente.get(f"/api/aluno/empresas/{empresa}", headers=aluno).json()
    assert detalhe["resultados"][0]["dre"]["multas"] == 3500
