"""Encargos legais da folha e do pró-labore (Lei 8.212/1991; Lei 8.036/1990; LC 123/2006)."""
from types import SimpleNamespace

import pytest

from app.motor.regras_mei import regras_mei
from app.motor.tradicional import apurar, preparar
from app.motor.tributos import FATOR_CLT, fator_clt, patronal_pro_labore
from tests.test_dependencias_sistemicas import DependenciasSistemicasTest as Base


def test_fatores_da_folha_seguem_o_metodo_de_martins():
    # 13,333 salários anuais × (1 + encargos) ÷ 11 meses trabalhados.
    assert fator_clt("SIMPLES_NACIONAL") == pytest.approx(13.3333 * 1.08 / 11, abs=1e-3)
    assert fator_clt("MEI") == pytest.approx(13.3333 * 1.11 / 11, abs=1e-3)
    assert fator_clt("LUCRO_PRESUMIDO") == pytest.approx(13.3333 * 1.358 / 11, abs=1e-3)
    assert set(FATOR_CLT) == {r for r in FATOR_CLT}


def test_patronal_sobre_pro_labore_so_fora_do_simples():
    assert patronal_pro_labore("SIMPLES_NACIONAL") == 0
    assert patronal_pro_labore("MEI") == 0
    assert patronal_pro_labore("LUCRO_PRESUMIDO") == pytest.approx(0.20)


@pytest.mark.parametrize("regime,esperado", [("SIMPLES_NACIONAL", 0.0), ("LUCRO_PRESUMIDO", 400.0)])
def test_dre_registra_encargo_do_pro_labore_por_regime(regime, esperado):
    base = Base()
    empresa = base.empresa_fisica()
    empresa["regime_tributario"] = regime
    decisao = base.decisao_fisica()
    decisao["simulacao"]["pro_labore"] = 2000
    preparo = preparar(empresa, decisao, base.parametros_fisicos(), 1)
    assert preparo["encargos_pro_labore"] == pytest.approx(esperado)
    dre = apurar(preparo, 80, base.sem_tributos)["dre"]
    assert dre["encargos_pro_labore"] == pytest.approx(esperado)
    assert dre["lucro_liquido"] == pytest.approx(
        dre["receita"] - sum(v for k, v in dre.items() if k not in ("receita", "lucro_liquido")))


def test_mei_tem_dois_empregados_a_partir_de_2027_e_teto_condicionado():
    turma = SimpleNamespace(
        configuracao_simulacao={"periodicidade": "SEMANAL", "data_inicio_simulada": "2026-12-31"},
        rodada_atual=1, teto_mei_anual=81000)
    assert regras_mei(turma, 1)["limite_empregados"] == 1  # semana de 31/12/2026
    assert regras_mei(turma, 2)["limite_empregados"] == 2  # 2027
    assert regras_mei(turma, 2)["teto_anual"] == 81000  # LC 238/2026, art. 3º: condição orçamentária
    turma.configuracao_simulacao["confirmacoes_normativas"] = {"LC238-2027-ORCAMENTO": True}
    assert regras_mei(turma, 2)["teto_anual"] == 110000
