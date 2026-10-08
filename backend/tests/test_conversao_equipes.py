from copy import deepcopy

from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar
from .test_avancado_api import _fechar, _decisao_avancada


def test_converter_preserva_historico_e_invalida_envio_atual(cliente, professor):
    turma = _criar_turma(cliente, professor, modo_jogo="TRADICIONAL", modo_equipe=False)
    aluno = cadastrar(cliente, "Ana", "conversao@aluno.iffar.edu.br")
    empresa = _entrar(cliente, aluno, turma["codigo"], "Empresa teste")
    _decisao_avancada(cliente, aluno, empresa, 1, comprar_mp=100, producao=100)
    _fechar(cliente, professor, turma, 1)
    _decisao_avancada(cliente, aluno, empresa, 2, producao=0)
    url = f"/api/professor/turmas/{turma['id']}/empresas/{empresa}"
    antes = cliente.get(url, headers=professor).json()
    r = cliente.put(f"/api/professor/turmas/{turma['id']}/parametros", headers=professor, json={"modo_equipe": True})
    assert r.status_code == 200, r.text
    depois = cliente.get(url, headers=professor).json()
    assert r.json()["modo_equipe"] is True
    assert depois["resultados"] == antes["resultados"]
    assert depois["decisoes"][0] == antes["decisoes"][0]
    assert depois["decisoes"][1]["versao"] == antes["decisoes"][1]["versao"] + 1
    assert len(depois["equipe"]["membros"]) == 1
    assert depois["equipe"]["membros"][0]["cargos"] == ["CEO"]
    assert depois["equipe"]["codigo_convite"]
    # Repeated save must not duplicate membership or invalidate again.
    assert cliente.put(f"/api/professor/turmas/{turma['id']}/parametros", headers=professor, json={"modo_equipe": True}).status_code == 200
    repetido = cliente.get(url, headers=professor).json()
    assert repetido["decisoes"] == depois["decisoes"]
    assert len(repetido["equipe"]["membros"]) == 1
    assert cliente.put(f"/api/professor/turmas/{turma['id']}/parametros", headers=professor, json={"modo_equipe": False}).status_code == 422


def test_concorrencia_muda_sem_recalcular_rodada_encerrada(cliente, professor):
    turma = _criar_turma(cliente, professor, modo_jogo="TRADICIONAL")
    aluno = cadastrar(cliente, "Bia", "concorrencia@aluno.iffar.edu.br")
    empresa = _entrar(cliente, aluno, turma["codigo"], "Empresa")
    _decisao_avancada(cliente, aluno, empresa, 1, comprar_mp=100, producao=100)
    _fechar(cliente, professor, turma, 1)
    url = f"/api/professor/turmas/{turma['id']}"
    detalhe = cliente.get(url, headers=professor).json()
    config = deepcopy(detalhe["turma"]["parametros"]["configuracao_simulacao"])
    resultados = cliente.get(f"{url}/empresas/{empresa}", headers=professor).json()["resultados"]
    config.update(concorrentes_virtuais=3, nivel_concorrencia="ALTA", estrutura_mercado="OLIGOPOLIO", forca_concorrentes="FORTE")
    r = cliente.put(f"{url}/parametros", headers=professor, json={"configuracao_simulacao": config})
    assert r.status_code == 200, r.text
    assert r.json()["parametros"]["configuracao_simulacao"]["concorrentes_virtuais"] == 3
    assert cliente.get(f"{url}/empresas/{empresa}", headers=professor).json()["resultados"] == resultados
    config["preco_maquina"] += 100
    assert cliente.put(f"{url}/parametros", headers=professor, json={"configuracao_simulacao": config}).status_code == 422
