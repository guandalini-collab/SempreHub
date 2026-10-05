import re

from .conftest import cadastrar


def test_professor_pode_usar_gmail(cliente):
    cadastrar(cliente, "Prof Gmail", "prof.pessoal@gmail.com", "PROFESSOR", "codigo-teste")


def test_aluno_continua_sem_gmail(cliente):
    r = cliente.post("/api/auth/cadastro", json={"nome": "Aluno", "email": "aluno@gmail.com", "senha": "senha-segura"})
    assert r.status_code == 422


def test_professor_cria_aluno_de_teste_com_email_qualquer(cliente, professor):
    r = cliente.post(
        "/api/professor/alunos-teste",
        headers=professor,
        json={"nome": "Aluno Teste 1", "email": "teste1@exemplo.inexistente", "senha": "teste-123"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["teste"] is True
    login = cliente.post("/api/auth/login", json={"email": "teste1@exemplo.inexistente", "senha": "teste-123"})
    assert login.status_code == 200
    assert login.json()["usuario"]["papel"] == "ALUNO"
    lista = cliente.get("/api/professor/alunos-teste", headers=professor).json()
    assert [a["email"] for a in lista] == ["teste1@exemplo.inexistente"]
    # Aluno não pode criar contas de teste
    aluno = {"Authorization": "Bearer " + login.json()["token"]}
    assert cliente.post("/api/professor/alunos-teste", headers=aluno, json={"nome": "X X", "email": "x@y.zz", "senha": "12345678"}).status_code == 403


def test_recuperacao_de_senha_por_link(cliente):
    cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    inexistente = cliente.post("/api/auth/esqueci-senha", json={"email": "ninguem@aluno.iffar.edu.br"})
    assert inexistente.status_code == 200 and "link_desenvolvimento" not in inexistente.json()

    r = cliente.post("/api/auth/esqueci-senha", json={"email": "ana@aluno.iffar.edu.br"})
    link = r.json()["link_desenvolvimento"]  # sem SMTP, em desenvolvimento
    token = re.search(r"redefinir-senha/(.+)$", link).group(1)

    r = cliente.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "nova-senha-1"})
    assert r.status_code == 200
    assert cliente.post("/api/auth/login", json={"email": "ana@aluno.iffar.edu.br", "senha": "nova-senha-1"}).status_code == 200
    assert cliente.post("/api/auth/login", json={"email": "ana@aluno.iffar.edu.br", "senha": "senha-segura"}).status_code == 401
    # Link de uso único
    assert cliente.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "outra-senha-2"}).status_code == 400


def test_professor_redefine_senha_de_aluno_da_turma(cliente, professor):
    turma = cliente.post("/api/professor/turmas", headers=professor, json={"nome": "Turma X"}).json()
    aluno = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    cliente.post(
        "/api/aluno/turmas/entrar",
        headers=aluno,
        json={"codigo": turma["codigo"], "nome_empresa": "Ana", "tipo_entrada_gem": "OPORTUNIDADE", "classe_dornelas": "SERIAL"},
    )
    detalhe = cliente.get(f"/api/professor/turmas/{turma['id']}", headers=professor).json()
    aluno_id = detalhe["empresas"][0]["aluno_id"]
    r = cliente.post(f"/api/professor/alunos/{aluno_id}/redefinir-senha", headers=professor, json={})
    assert r.status_code == 200
    nova = r.json()["nova_senha"]
    assert cliente.post("/api/auth/login", json={"email": "ana@aluno.iffar.edu.br", "senha": nova}).status_code == 200

    # Outro professor não pode redefinir a senha deste aluno
    outro = cadastrar(cliente, "Outro", "outro@gmail.com", "PROFESSOR", "codigo-teste")
    assert cliente.post(f"/api/professor/alunos/{aluno_id}/redefinir-senha", headers=outro, json={}).status_code == 404


def test_migracao_adiciona_coluna_em_banco_antigo(tmp_path):
    from sqlalchemy import create_engine, inspect, text

    import app.migracoes as mig

    banco = create_engine(f"sqlite:///{tmp_path/'antigo.db'}")
    with banco.begin() as c:
        c.execute(text("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome VARCHAR, email VARCHAR, senha_hash VARCHAR, papel VARCHAR, criado_em DATETIME)"))
    original = mig.engine
    mig.engine = banco
    try:
        mig.preparar_banco()
    finally:
        mig.engine = original
    colunas = {c["name"] for c in inspect(banco).get_columns("usuarios")}
    assert "criado_por_id" in colunas
