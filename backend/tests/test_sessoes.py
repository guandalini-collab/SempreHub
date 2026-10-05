"""Redefinir uma senha encerra sessões sem apagar a trajetória da empresa."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app import config
from app.routers import auth

from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar


@pytest.fixture(autouse=True)
def _recuperacao_local(monkeypatch):
    # Estes testes nunca enviam e-mail nem dependem de credenciais externas.
    monkeypatch.setattr(auth, "enviar_email", lambda *_: False)
    monkeypatch.setattr(auth, "email_configurado", lambda: False)
    monkeypatch.setattr(config, "AMBIENTE", "desenvolvimento")


def _login(cliente, email, senha="senha-segura"):
    resposta = cliente.post("/api/auth/login", json={"email": email, "senha": senha})
    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.json()['token']}"}


def _link_recuperacao(cliente, email):
    resposta = cliente.post("/api/auth/esqueci-senha", json={"email": email})
    assert resposta.status_code == 200
    return resposta.json()["link_desenvolvimento"].rsplit("/", 1)[-1]


def _redefinir_pelo_link(cliente, link, senha):
    return cliente.post("/api/auth/redefinir-senha", json={"token": link, "nova_senha": senha})


@pytest.mark.parametrize("nova_senha", ["nova-senha-segura", "senha-segura"])
def test_recuperacao_encerra_todas_sessoes_apenas_da_conta(cliente, professor, nova_senha):
    email = "ana@aluno.iffar.edu.br"
    cadastro = cadastrar(cliente, "Ana", email)
    login_1 = _login(cliente, email)
    login_2 = _login(cliente, email)
    outra_conta = cadastrar(cliente, "Bia", "bia@aluno.iffar.edu.br")
    sessoes_antigas = [cadastro, login_1, login_2]
    for sessao in sessoes_antigas:
        assert cliente.get("/api/auth/eu", headers=sessao).status_code == 200

    link = _link_recuperacao(cliente, email)
    outro_link = _link_recuperacao(cliente, email)
    resposta = _redefinir_pelo_link(cliente, link, nova_senha)
    assert resposta.status_code == 200
    nova_sessao = {"Authorization": f"Bearer {resposta.json()['token']}"}

    for sessao in sessoes_antigas:
        assert cliente.get("/api/auth/eu", headers=sessao).status_code == 401
        assert cliente.get("/api/aluno/empresas", headers=sessao).status_code == 401
    assert cliente.get("/api/auth/eu", headers=nova_sessao).status_code == 200
    novo_login = _login(cliente, email, nova_senha)
    assert cliente.get("/api/aluno/empresas", headers=novo_login).status_code == 200
    assert cliente.get("/api/auth/eu", headers=outra_conta).status_code == 200
    assert cliente.get("/api/professor/turmas", headers=professor).status_code == 200
    assert _redefinir_pelo_link(cliente, link, "senha-indevida").status_code == 400
    assert _redefinir_pelo_link(cliente, outro_link, "senha-indevida").status_code == 400
    if nova_senha != "senha-segura":
        assert cliente.post("/api/auth/login", json={"email": email, "senha": "senha-segura"}).status_code == 401


@pytest.mark.parametrize("responsavel", ["aluno", "professor"])
def test_token_legado_so_vale_ate_a_primeira_redefinicao(cliente, professor, responsavel):
    email = "ana@aluno.iffar.edu.br"
    aluno = cadastrar(cliente, "Ana", email)
    resposta = cliente.get("/api/auth/eu", headers=aluno)
    assert resposta.status_code == 200
    usuario_id = resposta.json()["id"]
    # Replica o formato de JWT emitido antes da implantação da versão de sessão.
    legado = jwt.encode(
        {"sub": str(usuario_id), "papel": "ALUNO", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        config.SECRET_KEY,
        algorithm="HS256",
    )
    sessao_legada = {"Authorization": f"Bearer {legado}"}
    assert cliente.get("/api/auth/eu", headers=sessao_legada).status_code == 200

    if responsavel == "aluno":
        link = _link_recuperacao(cliente, email)
        redefinicao = _redefinir_pelo_link(cliente, link, "nova-senha-segura")
    else:
        turma = _criar_turma(cliente, professor)
        _entrar(cliente, aluno, turma["codigo"], "Ana Doces")
        redefinicao = cliente.post(
            f"/api/professor/alunos/{usuario_id}/redefinir-senha",
            headers=professor,
            json={"nova_senha": "nova-senha-segura"},
        )
    assert redefinicao.status_code == 200
    assert cliente.get("/api/auth/eu", headers=sessao_legada).status_code == 401
    assert cliente.get("/api/auth/eu", headers=aluno).status_code == 401
    novo_login = _login(cliente, email, "nova-senha-segura")
    assert cliente.get("/api/auth/eu", headers=novo_login).status_code == 200


def test_redefinicao_pelo_professor_preserva_jogo_entre_rodadas(cliente, professor):
    turma = _criar_turma(cliente, professor, total_rodadas=2)
    email = "ana@aluno.iffar.edu.br"
    aluno = cadastrar(cliente, "Ana", email)
    outra_sessao = _login(cliente, email)
    empresa_id = _entrar(cliente, aluno, turma["codigo"], "Ana Doces", regime="SIMPLES_NACIONAL")
    caminho_empresa = f"/api/aluno/empresas/{empresa_id}"
    caminho_fechar = f"/api/professor/turmas/{turma['id']}/fechar-rodada"
    resposta = cliente.put(
        f"{caminho_empresa}/decisao",
        headers=aluno,
        json={"preco": 95, "contratar": 1, "emprestimo": 10000, "marketing": 500},
    )
    assert resposta.status_code == 200
    assert cliente.post(caminho_fechar, headers=professor, json={"evento": "NENHUM"}).status_code == 200
    resposta = cliente.get(caminho_empresa, headers=aluno)
    assert resposta.status_code == 200
    antes = resposta.json()
    assert antes["turma"]["rodada_atual"] == 2
    assert len(antes["resultados"]) == 1
    aluno_id = antes["empresa"]["aluno_id"]
    links_pendentes = [_link_recuperacao(cliente, email), _link_recuperacao(cliente, email)]

    # Mesmo mantendo a senha, a redefinição deve encerrar as sessões anteriores.
    redefinicao = cliente.post(
        f"/api/professor/alunos/{aluno_id}/redefinir-senha",
        headers=professor,
        json={"nova_senha": "senha-segura"},
    )
    assert redefinicao.status_code == 200
    for sessao in (aluno, outra_sessao):
        assert cliente.get(caminho_empresa, headers=sessao).status_code == 401
        assert cliente.put(f"{caminho_empresa}/decisao", headers=sessao, json={"preco": 105}).status_code == 401
    for link in links_pendentes:
        assert _redefinir_pelo_link(cliente, link, "senha-indevida").status_code == 400
    novo_login = _login(cliente, email)
    resposta = cliente.get(caminho_empresa, headers=novo_login)
    assert resposta.status_code == 200
    assert resposta.json() == antes  # Empresa, caixa, dívida, decisão e histórico intactos.

    # A nova sessão continua a mesma empresa e mantém o resultado da rodada 1.
    decisao = cliente.put(f"{caminho_empresa}/decisao", headers=novo_login, json={"preco": 105})
    assert decisao.status_code == 200
    assert decisao.json()["rodada"] == 2
    assert cliente.post(caminho_fechar, headers=professor, json={"evento": "NENHUM"}).status_code == 200
    resposta = cliente.get(caminho_empresa, headers=novo_login)
    assert resposta.status_code == 200
    final = resposta.json()
    assert final["empresa"]["id"] == empresa_id
    assert final["turma"]["status"] == "ENCERRADA"
    assert [resultado["rodada"] for resultado in final["resultados"]] == [1, 2]
    assert final["resultados"][0] == antes["resultados"][0]
    assert final["eventos"][0] == antes["eventos"][0]
    assert final["resultados"][1]["divida_final"] == antes["empresa"]["divida"]
    assert final["resultados"][1]["funcionarios"] == antes["empresa"]["funcionarios"]
