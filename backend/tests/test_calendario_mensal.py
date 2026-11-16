"""Rodada = mês de operação, sazonalidade da PMC/IBGE e janela de aula (Grupo 1)."""
from datetime import date, datetime, timedelta
import io
import json

import pytest
from fastapi import HTTPException

from app.motor.calendario import adaptar, periodo
from app.motor import sazonalidade_pmc as pmc
from app.prazos import validar_salvamento
from .test_equipes import _criar_equipe, _encerrar_formacao, _salvar


@pytest.fixture()
def db_sessao(cliente):
    from app.database import SessionLocal
    with SessionLocal() as sessao:
        yield sessao


def cfg(inicio="2026-11-01", setor="Colchões e Dormitório", rodada=1):
    return {"periodicidade": "MENSAL_CALENDARIO", "data_inicio_simulada": inicio,
            "rodada_inicio_calendario": rodada, "setor_mercado": setor}


def test_meses_civis_com_virada_de_ano_e_fevereiro():
    c = cfg("2026-11-01")
    meses = [periodo(c, r) for r in range(1, 6)]
    assert [m["inicio"] for m in meses] == ["2026-11-01", "2026-12-01", "2027-01-01", "2027-02-01", "2027-03-01"]
    assert [m["dias"] for m in meses] == [30, 31, 31, 28, 31]
    assert [m["ano_fiscal"] for m in meses] == [2026, 2026, 2027, 2027, 2027]
    assert all(m["fim_mes"] and m["fator_mensal"] == 1.0 for m in meses)
    assert periodo(cfg("2028-02-01"), 1)["dias"] == 29


def test_sazonalidade_vem_da_pmc_sem_pesos_de_eventos_nem_acrescimo_de_custos():
    dezembro = periodo(cfg("2026-12-01"), 1)
    saz = dezembro["sazonalidade"]
    assert saz["demanda"] == pmc.BASE["series"]["MOVEIS"][11]
    assert saz["atividade_pmc"] == "Móveis"
    assert saz["insumos"] == 1.0 and saz["frete"] == 1.0
    assert "Natal" in saz["eventos"]
    assert all(e["impacto_demanda"] == 0.0 for e in saz["detalhes_eventos"])
    assert "IBGE" in saz["fonte"] and "Estimativa técnica" in saz["estado"]
    assert periodo(cfg("2026-12-01", "Vestuário e Moda Básica"), 1)["sazonalidade"]["demanda"] == 1.73
    assert periodo(cfg("2026-12-01", "Pet Shop"), 1)["sazonalidade"]["demanda"] == 1.276
    assert periodo(cfg("2026-12-01", "Mochilas, Malas e Bolsas"), 1)["sazonalidade"]["atividade_pmc"] == "Tecidos, vestuário e calçados"


def test_setor_sem_serie_nao_recebe_sazonalidade_inventada():
    saz = periodo(cfg("2026-12-01", "Eletrônicos e Tecnologia"), 1)["sazonalidade"]
    assert saz["demanda"] == 1.0 and saz["atividade_pmc"] is None
    assert "sem série do IBGE" in saz["observacao"]


def test_proximo_mes_para_o_cockpit():
    novembro = periodo(cfg("2026-11-01"), 1)
    assert novembro["proximo_mes"]["mes"] == 12
    assert novembro["proximo_mes"]["fator"] == pmc.BASE["series"]["MOVEIS"][11]
    assert novembro["proximo_mes"]["variacao"] == pytest.approx(1.194 / 1.190 - 1, abs=1e-4)


def test_edicao_congelada_na_turma_prevalece():
    edicao = {"periodo": "2023–2026", "series": {"MOVEIS": [1.5] * 12}}
    c = {**cfg("2026-05-01"), "sazonalidade_pmc": edicao}
    assert periodo(c, 1)["sazonalidade"]["demanda"] == 1.5


def test_mes_nao_reescala_custos_nem_frete():
    p = {"configuracao_simulacao": {**cfg("2026-12-01"), "frete_padrao": 10.0},
         "custos_fixos_mensais": 1500, "taxa_juros_mensal": .025}
    a = adaptar(p, 1)
    assert a["custos_fixos_mensais"] == 1500
    assert a["taxa_juros_mensal"] == pytest.approx(.025)
    assert a["configuracao_simulacao"]["frete_padrao"] == 10.0


def _serie(anos, valor=lambda a, m: 100 + m):
    return {f"{a}{m:02d}": valor(a, m) for a in anos for m in range(1, 13)}


def test_calculo_usa_quatro_ultimos_anos_completos():
    valores = _serie([2021, 2022, 2023, 2024, 2025])
    valores["202601"] = 999  # ano incompleto é ignorado
    fatores = pmc.calcular(valores)
    assert len(fatores) == 12
    assert fatores[0] == round(101 / (sum(100 + m for m in range(1, 13)) / 12), 3)
    with pytest.raises(ValueError):
        pmc.calcular(_serie([2024, 2025]))


def _resposta_ibge(ano_final):
    resultados = []
    for atividade in pmc.ATIVIDADES.values():
        resultados.append({
            "classificacoes": [
                {"id": "11046", "categoria": {"56734": "Volume"}},
                {"id": "85", "categoria": {str(atividade["codigo"]): atividade["nome"]}},
            ],
            "series": [{"serie": {k: str(v) for k, v in _serie(range(ano_final - 3, ano_final + 1)).items()}}],
        })
    return json.dumps([{"resultados": resultados}]).encode()


class _Abrir:
    def __init__(self, corpo=None, erro=None):
        self.corpo, self.erro, self.urls = corpo, erro, []

    def __call__(self, url, timeout):
        self.urls.append(url)
        if self.erro:
            raise self.erro
        return io.BytesIO(self.corpo)


def test_atualizacao_anual_pela_api_e_falha_mantem_edicao(db_sessao):
    falha = _Abrir(erro=OSError("fora do ar"))
    assert pmc.atualizar(db_sessao, hoje=date(2027, 2, 10), abrir=falha) is False
    assert pmc.edicao_vigente(db_sessao)["periodo"] == "2022–2025"
    # Nova tentativa só no dia seguinte.
    assert pmc.atualizar(db_sessao, hoje=date(2027, 2, 10), abrir=falha) is False and len(falha.urls) == 1
    from app.models import SerieOficial
    db_sessao.query(SerieOficial).update({"tentado_em": datetime(2000, 1, 1)})
    certo = _Abrir(_resposta_ibge(2026))
    assert pmc.atualizar(db_sessao, hoje=date(2027, 2, 11), abrir=certo) is True
    assert "202301-202612" in certo.urls[0] and "8882" in certo.urls[0]
    assert pmc.edicao_vigente(db_sessao)["periodo"] == "2023–2026"
    # Já atualizada para o ano: não consulta de novo.
    assert pmc.atualizar(db_sessao, hoje=date(2027, 6, 1), abrir=certo) is False and len(certo.urls) == 1


def test_janela_maxima_de_duas_horas(cliente, professor):
    from .test_fluxo import _criar_turma
    turma = _criar_turma(cliente, professor, modo_jogo="TRADICIONAL", total_rodadas=2)
    url = f"/api/professor/turmas/{turma['id']}/agenda-academica"
    base = {"inicio_letivo": "2027-03-01", "fim_letivo": "2027-06-30", "dia_semana": 0, "recessos": []}
    assert cliente.put(url, headers=professor, json={**base, "horario_inicio": "19:30", "horario_fim": "21:31"}).status_code == 422
    assert cliente.put(url, headers=professor, json={**base, "horario_inicio": "19:30", "horario_fim": "19:00"}).status_code == 422
    assert cliente.put(url, headers=professor, json={**base, "horario_inicio": "19:30", "horario_fim": "21:30"}).status_code == 200


def test_fora_da_janela_so_consulta():
    from types import SimpleNamespace
    turma = SimpleNamespace(rodada_atual=1, prazo_numero_rodada=1,
                            abertura_rodada=datetime(2027, 3, 1, 22, 30), prazo_rodada=datetime(2027, 3, 2, 0, 30))
    validar_salvamento(turma, 1, datetime(2027, 3, 1, 23, 0))
    with pytest.raises(HTTPException, match="janela de decisão terminou"):
        validar_salvamento(turma, 1, datetime(2027, 3, 2, 0, 30))


def test_formacao_com_agenda_comeca_na_aula_seguinte(cliente, professor):
    equipe = _criar_equipe(cliente, professor, quantidade=2, total_rodadas=2, encerrar=False)
    turma_id = equipe["turma"]["id"]
    hoje = date.today()
    r = cliente.put(f"/api/professor/turmas/{turma_id}/agenda-academica", headers=professor, json={
        "inicio_letivo": hoje.isoformat(), "fim_letivo": (hoje + timedelta(days=120)).isoformat(),
        "dia_semana": (hoje + timedelta(days=3)).weekday(), "horario_inicio": "19:30", "horario_fim": "21:30", "recessos": [],
    })
    assert r.status_code == 200, r.text
    # Com a formação aberta não há janela de decisão.
    assert r.json()["abertura_rodada"] is None and r.json()["prazo_rodada"] is None
    turma = _encerrar_formacao(cliente, professor, turma_id).json()
    detalhe = cliente.get(f"/api/professor/turmas/{turma_id}", headers=professor).json()["turma"]
    primeira = detalhe["agenda_academica"]["rodadas"][0]
    assert detalhe["abertura_rodada"] == primeira["abre_em"]
    assert date.fromisoformat(primeira["aula"]) > hoje
    # (turma LEGADO: sem calendário; o mês da rodada 1 é testado em test_calendario)
    # Antes da aula, a decisão continua bloqueada.
    painel = cliente.get(f"/api/aluno/empresas/{equipe['id']}", headers=equipe["alunos"][0]["headers"]).json()
    from .decisoes import completar_decisao
    resposta = cliente.put(f"/api/aluno/empresas/{equipe['id']}/decisao", headers=equipe["alunos"][0]["headers"],
                           json=completar_decisao({"preco": 95, "rascunho": True, "versao": painel["equipe"]["versao_decisao"], "rodada": 1}))
    assert resposta.status_code == 403 and "calendário acadêmico" in resposta.json()["detail"]


def _turma_com_agenda(cliente, professor, rodadas=3):
    from .test_fluxo import _criar_turma
    turma = _criar_turma(cliente, professor, modo_jogo="TRADICIONAL", total_rodadas=rodadas)
    r = cliente.put(f"/api/professor/turmas/{turma['id']}/agenda-academica", headers=professor, json={
        "inicio_letivo": "2027-03-01", "fim_letivo": "2027-06-30", "dia_semana": 0,
        "horario_inicio": "19:30", "horario_fim": "21:30", "recessos": [],
    })
    assert r.status_code == 200, r.text
    return turma


def test_extensao_pontual_da_rodada_1_e_rodada_2_na_aula_seguinte(cliente, professor):
    turma = _turma_com_agenda(cliente, professor)
    url = f"/api/professor/turmas/{turma['id']}/prorrogacao"
    # Aula 1 em 01/03/2027 (segunda): aberta até quinta, 04/03, 23h59.
    r = cliente.put(url, headers=professor, json={"rodada": 1, "data": "2027-03-04", "horario": "23:59"})
    assert r.status_code == 200, r.text
    rodadas = r.json()["agenda_academica"]["rodadas"]
    assert rodadas[0]["abre_em"] == "2027-03-01T22:30:00Z"
    assert rodadas[0]["fecha_em"] == "2027-03-05T02:59:00Z" and rodadas[0]["prorrogada"]
    assert r.json()["prazo_rodada"].startswith("2027-03-05T02:59:00")
    # A rodada 2 não abre ao fechar a 1: abre na aula seguinte, só no horário da aula.
    assert rodadas[1]["aula"] == "2027-03-08"
    assert rodadas[1]["fecha_em"] == "2027-03-09T00:30:00Z" and not rodadas[1]["prorrogada"]
    # Extensão que passa da aula seguinte empurra as rodadas para as próximas aulas.
    r = cliente.put(url, headers=professor, json={"rodada": 1, "data": "2027-03-09", "horario": "12:00"})
    assert [x["aula"] for x in r.json()["agenda_academica"]["rodadas"]] == ["2027-03-01", "2027-03-15", "2027-03-22"]
    # Cancelar volta ao horário da aula.
    r = cliente.put(url, headers=professor, json={"rodada": 1})
    rodadas = r.json()["agenda_academica"]["rodadas"]
    assert rodadas[0]["fecha_em"] == "2027-03-02T00:30:00Z" and rodadas[1]["aula"] == "2027-03-08"


def test_extensao_validada(cliente, professor):
    turma = _turma_com_agenda(cliente, professor)
    url = f"/api/professor/turmas/{turma['id']}/prorrogacao"
    assert cliente.put(url, headers=professor, json={"rodada": 1, "data": "2020-01-01", "horario": "10:00"}).status_code == 422
    assert cliente.put(url, headers=professor, json={"rodada": 1, "data": "2027-03-04"}).status_code == 422
    assert cliente.put(url, headers=professor, json={"rodada": 9, "data": "2027-03-04", "horario": "23:59"}).status_code == 422
    # Fechamento antes da abertura da própria rodada.
    r = cliente.put(url, headers=professor, json={"rodada": 2, "data": "2027-03-08", "horario": "18:00"})
    assert r.status_code == 422 and "antes da abertura" in r.json()["detail"]
    from .test_fluxo import _criar_turma
    sem_agenda = _criar_turma(cliente, professor, modo_jogo="TRADICIONAL")
    assert cliente.put(f"/api/professor/turmas/{sem_agenda['id']}/prorrogacao", headers=professor,
                       json={"rodada": 1, "data": "2027-03-04", "horario": "23:59"}).status_code == 422


def test_extensao_definida_com_formacao_aberta_vale_no_encerramento(cliente, professor):
    equipe = _criar_equipe(cliente, professor, quantidade=2, total_rodadas=2, encerrar=False)
    turma_id = equipe["turma"]["id"]
    r = cliente.put(f"/api/professor/turmas/{turma_id}/agenda-academica", headers=professor, json={
        "inicio_letivo": "2027-03-01", "fim_letivo": "2027-06-30", "dia_semana": 0,
        "horario_inicio": "19:30", "horario_fim": "21:30", "recessos": [],
    })
    assert r.status_code == 200
    assert cliente.put(f"/api/professor/turmas/{turma_id}/prorrogacao", headers=professor,
                       json={"rodada": 1, "data": "2027-03-03", "horario": "22:00"}).status_code == 200
    assert cliente.get(f"/api/professor/turmas/{turma_id}", headers=professor).json()["turma"]["prazo_rodada"] is None
    _encerrar_formacao(cliente, professor, turma_id)
    turma = cliente.get(f"/api/professor/turmas/{turma_id}", headers=professor).json()["turma"]
    assert turma["prazo_rodada"].startswith("2027-03-04T01:00:00")
    assert turma["agenda_academica"]["rodadas"][1]["aula"] == "2027-03-08"
