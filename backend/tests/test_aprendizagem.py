from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar


def test_relatorio_e_news_preservam_primeira_rodada_e_restringem_acesso(cliente, professor):
    turma = _criar_turma(cliente, professor, total_rodadas=3)
    aluno = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    outro = cadastrar(cliente, "Bia", "bia@aluno.iffar.edu.br")
    empresa = _entrar(cliente, aluno, turma["codigo"], "Empresa Ana")
    base = f"/api/aluno/empresas/{empresa}"
    assert cliente.get(base + "/relatorio-primeira-rodada", headers=aluno).status_code == 409
    assert cliente.get(base + "/news", headers=aluno).json()["edicoes"] == []
    assert cliente.get(base + "/news", headers=outro).status_code == 404
    assert cliente.get(base + "/relatorio-primeira-rodada").status_code == 401
    for rodada in (1, 2):
        resposta = cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento":"NENHUM"})
        assert resposta.status_code == 200, resposta.text
        relatorio = cliente.get(base + "/relatorio-primeira-rodada", headers=aluno).json()
        if rodada == 1:
            anterior = relatorio
        else:
            assert relatorio == anterior
    assert relatorio["resultado"]["rodada"] == 1
    assert len(relatorio["midias"]) >= 20
    assert len(cliente.get(base + "/news", headers=aluno).json()["edicoes"]) == 2
    assert cliente.get("/api/educacao/midias").status_code == 200
