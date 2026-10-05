"""Empresas compartilhadas exigem decisões atuais aprovadas por toda a equipe."""

from copy import deepcopy
import csv
import io
import json

import pytest

from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar


def _aluno(cliente, indice):
    email = f"equipe{indice}@aluno.iffar.edu.br"
    headers = cadastrar(cliente, f"Aluno {indice}", email)
    resposta = cliente.get("/api/auth/eu", headers=headers)
    assert resposta.status_code == 200
    return {"id": resposta.json()["id"], "email": email, "headers": headers}


def _painel(cliente, empresa_id, aluno):
    resposta = cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno["headers"])
    assert resposta.status_code == 200
    return resposta.json()


def _criar_equipe(cliente, professor, quantidade=3, total_rodadas=3):
    turma = _criar_turma(cliente, professor, modo_equipe=True, total_rodadas=total_rodadas)
    assert turma["modo_equipe"] is True
    fundador = _aluno(cliente, 0)
    empresa_id = _entrar(cliente, fundador["headers"], turma["codigo"], "Empresa Compartilhada", regime="SIMPLES_NACIONAL")
    painel = _painel(cliente, empresa_id, fundador)
    codigo = painel["equipe"]["codigo_convite"]
    assert codigo
    alunos = [fundador]
    for indice in range(1, quantidade):
        aluno = _aluno(cliente, indice)
        resposta = cliente.post("/api/aluno/equipes/entrar", headers=aluno["headers"], json={"codigo": codigo})
        assert resposta.status_code == 201
        assert resposta.json()["empresa"]["id"] == empresa_id
        alunos.append(aluno)
    return {"turma": turma, "id": empresa_id, "codigo": codigo, "alunos": alunos}


def _cargos(alunos):
    return [
        {"aluno_id": alunos[0]["id"], "cargos": ["CEO", "CFO"]},
        {"aluno_id": alunos[1]["id"], "cargos": ["CMO", "CHRO"]},
        {"aluno_id": alunos[2]["id"], "cargos": ["COO"]},
    ]


def _configurar(cliente, equipe, membros=None):
    resposta = cliente.put(
        f"/api/aluno/empresas/{equipe['id']}/equipe",
        headers=equipe["alunos"][0]["headers"],
        json={"membros": membros if membros is not None else _cargos(equipe["alunos"])},
    )
    assert resposta.status_code == 200
    return resposta.json()


def _salvar(cliente, equipe, aluno=None, **dados):
    aluno = aluno or equipe["alunos"][0]
    painel = _painel(cliente, equipe["id"], aluno)
    versao = painel["equipe"]["versao_decisao"]
    resposta = cliente.put(
        f"/api/aluno/empresas/{equipe['id']}/decisao",
        headers=aluno["headers"],
        json={"preco": 95, "versao": versao, "rodada": painel["turma"]["rodada_atual"], **dados},
    )
    assert resposta.status_code == 200
    assert resposta.json()["versao"] > versao
    return resposta.json()


def _aprovar(cliente, equipe, aluno, versao):
    rodada = _painel(cliente, equipe["id"], aluno)["turma"]["rodada_atual"]
    resposta = cliente.post(
        f"/api/aluno/empresas/{equipe['id']}/aprovar",
        headers=aluno["headers"],
        json={"versao": versao, "rodada": rodada},
    )
    assert resposta.status_code == 200
    return resposta.json()


def _fechar(cliente, equipe, professor, evento="NENHUM"):
    rodada = _painel(cliente, equipe["id"], equipe["alunos"][0])["turma"]["rodada_atual"]
    return cliente.post(
        f"/api/professor/turmas/{equipe['turma']['id']}/fechar-rodada",
        headers=professor,
        json={"evento": evento, "rodada": rodada},
    )


def _fechamento_bloqueado_preserva_painel(cliente, equipe, professor):
    fundador = equipe["alunos"][0]
    antes = _painel(cliente, equipe["id"], fundador)
    resposta = _fechar(cliente, equipe, professor)
    assert resposta.status_code == 422
    assert _painel(cliente, equipe["id"], fundador) == antes


@pytest.fixture()
def equipe(cliente, professor):
    return _criar_equipe(cliente, professor)


def test_modo_individual_continua_sem_convite_ou_aprovacao(cliente, professor):
    turma = _criar_turma(cliente, professor, total_rodadas=2)
    assert turma["modo_equipe"] is False
    aluno = _aluno(cliente, 0)
    empresa_id = _entrar(cliente, aluno["headers"], turma["codigo"], "Empresa Individual")
    assert _painel(cliente, empresa_id, aluno)["equipe"] is None
    resposta = cliente.put(f"/api/aluno/empresas/{empresa_id}/decisao", headers=aluno["headers"], json={"preco": 90})
    assert resposta.status_code == 200
    detalhe = cliente.get(f"/api/professor/turmas/{turma['id']}", headers=professor).json()
    assert detalhe["empresas"][0]["decisao_enviada"] is True
    resposta = cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "NENHUM"})
    assert resposta.status_code == 200
    # O fluxo individual mantém a repetição automática quando não há envio.
    assert cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "NENHUM"}).status_code == 200
    final = _painel(cliente, empresa_id, aluno)
    assert final["turma"]["status"] == "ENCERRADA"
    assert [resultado["rodada"] for resultado in final["resultados"]] == [1, 2]
    assert final["ultima_decisao"]["automatica"] is True


def test_membros_compartilham_empresa_e_so_fundador_organiza_cargos(cliente, professor, equipe):
    fundador, membro, terceiro = equipe["alunos"]
    inicial = _painel(cliente, equipe["id"], fundador)["equipe"]
    assert inicial["pode_gerenciar"] is True
    assert next(m for m in inicial["membros"] if m["aluno_id"] == fundador["id"])["cargos"] == ["CEO"]
    _configurar(cliente, equipe)
    for aluno in (fundador, membro, terceiro):
        painel = _painel(cliente, equipe["id"], aluno)
        assert painel["empresa"]["id"] == equipe["id"]
        assert {m["aluno_id"] for m in painel["equipe"]["membros"]} == {a["id"] for a in equipe["alunos"]}
        assert painel["equipe"]["pode_gerenciar"] is (aluno is fundador)
        empresas = cliente.get("/api/aluno/empresas", headers=aluno["headers"])
        assert empresas.status_code == 200
        assert [registro["empresa"]["id"] for registro in empresas.json()] == [equipe["id"]]
    resposta = cliente.put(
        f"/api/aluno/empresas/{equipe['id']}/equipe",
        headers=membro["headers"],
        json={"membros": _cargos(equipe["alunos"])},
    )
    assert resposta.status_code == 403

    estranho = _aluno(cliente, 3)
    outra_empresa = _entrar(cliente, estranho["headers"], equipe["turma"]["codigo"], "Outra Equipe")
    assert outra_empresa != equipe["id"]
    assert cliente.get(f"/api/aluno/empresas/{equipe['id']}", headers=estranho["headers"]).status_code == 404
    assert cliente.post(f"/api/aluno/empresas/{equipe['id']}/aprovar", headers=estranho["headers"], json={"versao": 1, "rodada": 1}).status_code == 404
    assert cliente.put(f"/api/aluno/empresas/{equipe['id']}/decisao", headers=estranho["headers"], json={"preco": 80, "versao": 0}).status_code == 404
    assert cliente.get(f"/api/aluno/empresas/{outra_empresa}", headers=membro["headers"]).status_code == 404
    detalhe = cliente.get(f"/api/professor/turmas/{equipe['turma']['id']}", headers=professor).json()
    assert len(detalhe["empresas"]) == 2  # Três alunos representam uma só empresa.


@pytest.mark.parametrize("problema", ["cargo_duplicado", "ceo_transferido", "cargo_desconhecido", "membro_ausente", "membro_estranho", "sem_cargo"])
def test_cargos_invalidos_nao_alteram_equipe(cliente, equipe, problema):
    membros = deepcopy(_cargos(equipe["alunos"]))
    if problema == "cargo_duplicado":
        membros[1]["cargos"].append("CFO")
    elif problema == "ceo_transferido":
        membros[0]["cargos"].remove("CEO")
        membros[1]["cargos"].append("CEO")
    elif problema == "cargo_desconhecido":
        membros[1]["cargos"].append("AUDITOR")
    elif problema == "membro_ausente":
        membros.pop()
    elif problema == "membro_estranho":
        membros[2]["aluno_id"] = 999999
    elif problema == "sem_cargo":
        membros[2]["cargos"] = []
    fundador = equipe["alunos"][0]
    antes = _painel(cliente, equipe["id"], fundador)
    resposta = cliente.put(f"/api/aluno/empresas/{equipe['id']}/equipe", headers=fundador["headers"], json={"membros": membros})
    assert resposta.status_code == 422
    assert _painel(cliente, equipe["id"], fundador) == antes


def test_inscricao_unica_por_turma_e_limite_de_cinco_membros(cliente, professor):
    equipe = _criar_equipe(cliente, professor, quantidade=5)
    sexto = _aluno(cliente, 5)
    resposta = cliente.post("/api/aluno/equipes/entrar", headers=sexto["headers"], json={"codigo": equipe["codigo"]})
    assert resposta.status_code == 422
    assert len(_painel(cliente, equipe["id"], equipe["alunos"][0])["equipe"]["membros"]) == 5
    assert cliente.post("/api/aluno/equipes/entrar", headers=equipe["alunos"][1]["headers"], json={"codigo": equipe["codigo"]}).status_code == 409
    outra_empresa = _entrar(cliente, sexto["headers"], equipe["turma"]["codigo"], "Segunda Equipe")
    outro_convite = _painel(cliente, outra_empresa, sexto)["equipe"]["codigo_convite"]
    assert cliente.post("/api/aluno/equipes/entrar", headers=equipe["alunos"][1]["headers"], json={"codigo": outro_convite}).status_code == 409
    resposta = cliente.post(
        "/api/aluno/turmas/entrar",
        headers=equipe["alunos"][1]["headers"],
        json={"codigo": equipe["turma"]["codigo"], "nome_empresa": "Duplicada", "tipo_entrada_gem": "OPORTUNIDADE", "classe_dornelas": "SERIAL"},
    )
    assert resposta.status_code == 409


def test_numero_minimo_e_cargos_obrigatorios_bloqueiam_rodada_sem_perder_dados(cliente, professor):
    equipe = _criar_equipe(cliente, professor, quantidade=1)
    _salvar(cliente, equipe, emprestimo=10000)
    _fechamento_bloqueado_preserva_painel(cliente, equipe, professor)
    for indice in (1, 2):
        aluno = _aluno(cliente, indice)
        assert cliente.post("/api/aluno/equipes/entrar", headers=aluno["headers"], json={"codigo": equipe["codigo"]}).status_code == 201
        equipe["alunos"].append(aluno)
    cargos = _cargos(equipe["alunos"])
    cargos[1]["cargos"].remove("CHRO")
    _configurar(cliente, equipe, cargos)
    pendencias = _painel(cliente, equipe["id"], equipe["alunos"][0])["equipe"]["pendencias"]
    assert any("CHRO" in pendencia for pendencia in pendencias)
    _fechamento_bloqueado_preserva_painel(cliente, equipe, professor)


def test_versao_obrigatoria_e_edicao_concorrente_nao_sobrescreve_decisao(cliente, professor, equipe):
    _configurar(cliente, equipe)
    fundador, membro, terceiro = equipe["alunos"]
    assert cliente.put(f"/api/aluno/empresas/{equipe['id']}/decisao", headers=fundador["headers"], json={"preco": 90}).status_code == 422
    primeira = _salvar(cliente, equipe, emprestimo=10000)
    _aprovar(cliente, equipe, fundador, primeira["versao"])
    _aprovar(cliente, equipe, membro, primeira["versao"])
    antes = _painel(cliente, equipe["id"], fundador)
    assert antes["equipe"]["pronta"] is False
    detalhe = cliente.get(f"/api/professor/turmas/{equipe['turma']['id']}", headers=professor).json()
    assert detalhe["empresas"][0]["decisao_enviada"] is False
    _fechamento_bloqueado_preserva_painel(cliente, equipe, professor)
    resposta = cliente.put(
        f"/api/aluno/empresas/{equipe['id']}/decisao",
        headers=terceiro["headers"],
        json={"preco": 1, "versao": primeira["versao"] - 1, "rodada": 1},
    )
    assert resposta.status_code == 409
    assert _painel(cliente, equipe["id"], fundador) == antes

    segunda = _salvar(cliente, equipe, aluno=terceiro, preco=105, marketing=400)
    assert segunda["versao"] == primeira["versao"] + 1
    depois = _painel(cliente, equipe["id"], fundador)
    assert depois["decisao_atual"]["preco"] == 105
    assert depois["equipe"]["aprovacoes"] == []
    assert depois["equipe"]["aprovada_por_mim"] is False
    assert all(registro in depois["equipe"]["historico"] for registro in antes["equipe"]["historico"])
    assert cliente.post(f"/api/aluno/empresas/{equipe['id']}/aprovar", headers=membro["headers"], json={"versao": primeira["versao"], "rodada": 1}).status_code == 409
    for aluno in equipe["alunos"]:
        _aprovar(cliente, equipe, aluno, segunda["versao"])
    pronta = _painel(cliente, equipe["id"], fundador)["equipe"]
    assert pronta["pronta"] is True
    assert {aprovacao["aluno_id"] for aprovacao in pronta["aprovacoes"]} == {aluno["id"] for aluno in equipe["alunos"]}
    assert {aprovacao["versao"] for aprovacao in pronta["aprovacoes"]} == {segunda["versao"]}
    detalhe = cliente.get(f"/api/professor/turmas/{equipe['turma']['id']}", headers=professor).json()
    assert detalhe["empresas"][0]["decisao_enviada"] is True

    # O professor recebe as assinaturas antigas e atuais, mesmo que só a última
    # versão da decisão tenha sido usada para calcular o resultado da rodada.
    assert _fechar(cliente, equipe, professor).status_code == 200
    exportacao = cliente.get(f"/api/professor/turmas/{equipe['turma']['id']}/exportar.csv", headers=professor)
    assert exportacao.status_code == 200
    linhas = list(csv.DictReader(io.StringIO(exportacao.text.lstrip("\ufeff")), delimiter=";"))
    assert len(linhas) == 1
    assert int(linhas[0]["versao_decisao"]) == segunda["versao"]
    assinaturas = json.loads(linhas[0]["aprovacoes"])
    antigas = [assinatura for assinatura in assinaturas if assinatura["versao"] == primeira["versao"]]
    atuais = [assinatura for assinatura in assinaturas if assinatura["versao"] == segunda["versao"]]
    assert len(antigas) == 2
    assert {assinatura["aluno_id"] for assinatura in antigas} == {fundador["id"], membro["id"]}
    assert len(atuais) == 3
    assert {assinatura["aluno_id"] for assinatura in atuais} == {aluno["id"] for aluno in equipe["alunos"]}
    participacao = json.loads(linhas[0]["participacao_individual"])
    assert len([registro for registro in participacao if registro["acao"] == "APROVAR_DECISAO"]) == 5


def test_rodada_e_obrigatoria_em_previa_edicao_e_assinatura_da_equipe(cliente, equipe):
    _configurar(cliente, equipe)
    fundador = equipe["alunos"][0]
    empresa_url = f"/api/aluno/empresas/{equipe['id']}"
    antes = _painel(cliente, equipe["id"], fundador)
    sem_rodada = {"preco": 95, "versao": 0}
    assert cliente.post(f"{empresa_url}/previsao", headers=fundador["headers"], json=sem_rodada).status_code == 422
    assert cliente.put(f"{empresa_url}/decisao", headers=fundador["headers"], json=sem_rodada).status_code == 422
    assert _painel(cliente, equipe["id"], fundador) == antes

    decisao = _salvar(cliente, equipe)
    antes = _painel(cliente, equipe["id"], fundador)
    assert cliente.post(f"{empresa_url}/aprovar", headers=fundador["headers"], json={"versao": decisao["versao"]}).status_code == 422
    assert _painel(cliente, equipe["id"], fundador) == antes
    _aprovar(cliente, equipe, fundador, decisao["versao"])
    assert _painel(cliente, equipe["id"], fundador)["equipe"]["aprovada_por_mim"] is True


def test_aprovacao_e_assinada_pela_conta_autenticada(cliente, professor, equipe):
    _configurar(cliente, equipe)
    decisao = _salvar(cliente, equipe)
    fundador, membro, terceiro = equipe["alunos"]
    resposta = cliente.post(
        f"/api/aluno/empresas/{equipe['id']}/aprovar",
        headers=membro["headers"],
        json={"versao": decisao["versao"], "rodada": 1, "aluno_id": terceiro["id"]},
    )
    assert resposta.status_code == 200
    aprovacoes = _painel(cliente, equipe["id"], fundador)["equipe"]["aprovacoes"]
    assert [aprovacao["aluno_id"] for aprovacao in aprovacoes] == [membro["id"]]
    repetida = cliente.post(f"/api/aluno/empresas/{equipe['id']}/aprovar", headers=membro["headers"], json={"versao": decisao["versao"], "rodada": 1})
    assert repetida.status_code in (200, 409)
    assert len(_painel(cliente, equipe["id"], fundador)["equipe"]["aprovacoes"]) == 1
    assert cliente.post(f"/api/aluno/empresas/{equipe['id']}/aprovar", headers=professor, json={"versao": decisao["versao"]}).status_code == 403


def test_duas_rodadas_preservam_empresa_decisoes_resultados_e_assinaturas(cliente, professor):
    equipe = _criar_equipe(cliente, professor, total_rodadas=2)
    _configurar(cliente, equipe)
    fundador = equipe["alunos"][0]
    primeira = _salvar(cliente, equipe, emprestimo=10000, contratar=1, marketing=500, pd=300)
    for aluno in equipe["alunos"]:
        _aprovar(cliente, equipe, aluno, primeira["versao"])
    painel_aprovado = _painel(cliente, equipe["id"], fundador)
    primeira = painel_aprovado["decisao_atual"]
    historico_primeiro = painel_aprovado["equipe"]["historico"]
    assert _fechar(cliente, equipe, professor, evento="GREVE_LOGISTICA").status_code == 200
    depois_primeiro = _painel(cliente, equipe["id"], fundador)
    assert depois_primeiro["turma"]["rodada_atual"] == 2
    assert len(depois_primeiro["resultados"]) == 1
    assert depois_primeiro["empresa"]["divida"] == 10000
    assert depois_primeiro["ultima_decisao"]["rodada"] == 1
    assert depois_primeiro["equipe"]["aprovacoes"] == []
    assert depois_primeiro["equipe"]["aprovada_por_mim"] is False
    assert depois_primeiro["equipe"]["pronta"] is False
    assert all(registro in depois_primeiro["equipe"]["historico"] for registro in historico_primeiro)

    # Versão zero pode existir em qualquer rodada: o número da rodada também
    # protege contra uma aba antiga gravar decisões na rodada seguinte.
    decisao_antiga = {"preco": 1, "versao": 0, "rodada": 1}
    assert cliente.put(f"/api/aluno/empresas/{equipe['id']}/decisao", headers=fundador["headers"], json=decisao_antiga).status_code == 409
    assert cliente.post(f"/api/aluno/empresas/{equipe['id']}/previsao", headers=fundador["headers"], json=decisao_antiga).status_code == 409
    fechar_url = f"/api/professor/turmas/{equipe['turma']['id']}/fechar-rodada"
    assert cliente.post(fechar_url, headers=professor, json={"evento": "NENHUM", "rodada": 1}).status_code == 409
    assert _painel(cliente, equipe["id"], fundador) == depois_primeiro

    atrasado = _aluno(cliente, 3)
    assert cliente.post("/api/aluno/equipes/entrar", headers=atrasado["headers"], json={"codigo": equipe["codigo"]}).status_code == 422
    assert cliente.put(f"/api/aluno/empresas/{equipe['id']}/equipe", headers=fundador["headers"], json={"membros": _cargos(equipe["alunos"])}).status_code == 422
    assert _painel(cliente, equipe["id"], fundador) == depois_primeiro

    segunda = _salvar(cliente, equipe, aluno=equipe["alunos"][2], preco=105, amortizacao=2000)
    assert cliente.post(f"/api/aluno/empresas/{equipe['id']}/aprovar", headers=fundador["headers"], json={"versao": segunda["versao"], "rodada": 1}).status_code == 409
    _aprovar(cliente, equipe, fundador, segunda["versao"])
    _fechamento_bloqueado_preserva_painel(cliente, equipe, professor)
    for aluno in equipe["alunos"][1:]:
        _aprovar(cliente, equipe, aluno, segunda["versao"])
    assert _fechar(cliente, equipe, professor).status_code == 200
    for aluno in equipe["alunos"]:
        final = _painel(cliente, equipe["id"], aluno)
        assert final["empresa"]["id"] == equipe["id"]
        assert final["turma"]["status"] == "ENCERRADA"
        assert [resultado["rodada"] for resultado in final["resultados"]] == [1, 2]
        assert final["resultados"][0] == depois_primeiro["resultados"][0]
        assert final["eventos"][0] == depois_primeiro["eventos"][0]
        assert final["empresa"]["divida"] == 8000
        assert all(registro in final["equipe"]["historico"] for registro in historico_primeiro)
    empresa_professor = cliente.get(f"/api/professor/turmas/{equipe['turma']['id']}/empresas/{equipe['id']}", headers=professor)
    assert empresa_professor.status_code == 200
    assert [decisao["rodada"] for decisao in empresa_professor.json()["decisoes"]] == [1, 2]
    assert empresa_professor.json()["decisoes"][0] == primeira


def test_professor_redefine_senha_de_membro_sem_ser_dono_da_empresa(cliente, professor, equipe):
    fundador, membro, _ = equipe["alunos"]
    outro_professor = cadastrar(cliente, "Outro Professor", "outro@gmail.com", "PROFESSOR", "codigo-teste")
    url = f"/api/professor/alunos/{membro['id']}/redefinir-senha"
    assert cliente.post(url, headers=outro_professor, json={"nova_senha": "senha-indevida"}).status_code == 404
    resposta = cliente.post(url, headers=professor, json={"nova_senha": "nova-senha-segura"})
    assert resposta.status_code == 200
    assert cliente.get(f"/api/aluno/empresas/{equipe['id']}", headers=membro["headers"]).status_code == 401
    assert _painel(cliente, equipe["id"], fundador)["empresa"]["id"] == equipe["id"]
    login = cliente.post("/api/auth/login", json={"email": membro["email"], "senha": "nova-senha-segura"})
    assert login.status_code == 200
    membro["headers"] = {"Authorization": f"Bearer {login.json()['token']}"}
    assert _painel(cliente, equipe["id"], membro)["empresa"]["id"] == equipe["id"]


def test_login_da_equipe_tem_auditoria_sem_registrar_credenciais(cliente, professor, equipe):
    fundador, membro, _ = equipe["alunos"]
    antes = _painel(cliente, equipe["id"], fundador)["equipe"]["historico"]
    assert cliente.post("/api/auth/login", json={"email": membro["email"], "senha": "senha-incorreta"}).status_code == 401
    assert _painel(cliente, equipe["id"], fundador)["equipe"]["historico"] == antes
    login = cliente.post("/api/auth/login", json={"email": membro["email"], "senha": "senha-segura"})
    assert login.status_code == 200
    historico = _painel(cliente, equipe["id"], fundador)["equipe"]["historico"]
    acessos = [registro for registro in historico if registro["acao"] == "LOGIN"]
    assert len(acessos) == 1
    assert acessos[0]["aluno_id"] == membro["id"]
    assert acessos[0]["aluno"] == "Aluno 1"
    assert all(registro in historico for registro in antes)
    texto = json.dumps(historico, ensure_ascii=False)
    assert "senha-segura" not in texto
    assert "senha-incorreta" not in texto
    assert login.json()["token"] not in texto
    detalhe = cliente.get(f"/api/professor/turmas/{equipe['turma']['id']}/empresas/{equipe['id']}", headers=professor)
    assert detalhe.status_code == 200
    assert acessos[0] in detalhe.json()["equipe"]["historico"]


def test_login_concorrente_a_redefinicao_nao_emite_sessao_valida_com_senha_antiga(cliente, equipe, monkeypatch):
    from sqlalchemy.orm import Session

    from app.database import engine
    from app.models import Usuario
    from app.routers import auth
    from app.seguranca import trocar_senha

    membro = equipe["alunos"][1]
    verificar_original = auth.verificar_senha
    redefinida = False

    def verificar_e_redefinir(senha, senha_hash):
        nonlocal redefinida
        correta = verificar_original(senha, senha_hash)
        if correta and not redefinida:
            # Outra requisição redefine a senha depois da comparação do hash e
            # antes que o login atual confirme seus eventos de auditoria.
            with Session(engine) as sessao:
                usuario = sessao.get(Usuario, membro["id"])
                trocar_senha(sessao, usuario, "senha-redefinida")
                sessao.commit()
            redefinida = True
        return correta

    monkeypatch.setattr(auth, "verificar_senha", verificar_e_redefinir)
    login_antigo = cliente.post("/api/auth/login", json={"email": membro["email"], "senha": "senha-segura"})
    assert login_antigo.status_code == 200
    assert redefinida is True
    sessao_antiga = {"Authorization": f"Bearer {login_antigo.json()['token']}"}
    assert cliente.get("/api/auth/eu", headers=sessao_antiga).status_code == 401
    assert cliente.get("/api/auth/eu", headers=membro["headers"]).status_code == 401

    novo_login = cliente.post("/api/auth/login", json={"email": membro["email"], "senha": "senha-redefinida"})
    assert novo_login.status_code == 200
    membro["headers"] = {"Authorization": f"Bearer {novo_login.json()['token']}"}
    assert _painel(cliente, equipe["id"], membro)["empresa"]["id"] == equipe["id"]
