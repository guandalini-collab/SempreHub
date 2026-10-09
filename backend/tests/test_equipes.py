from .decisoes import completar_decisao
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
    equipe = {"turma": turma, "id": empresa_id, "codigo": codigo, "alunos": alunos}
    if quantidade >= 3:
        for aluno in alunos[:quantidade//2+1]:
            assert cliente.post(f"/api/aluno/empresas/{empresa_id}/lider", headers=aluno["headers"], json={"aluno_id": fundador["id"], "rodada": 1}).status_code == 200
    return equipe


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
        json=completar_decisao({"preco": 95, "rascunho": True, "versao": versao, "rodada": painel["turma"]["rodada_atual"], **dados}),
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


def test_lider_envia_e_demais_integrantes_apenas_visualizam(cliente, professor, equipe):
    lider, colega, _ = equipe["alunos"]
    salva = _salvar(cliente, equipe)
    base = f"/api/aluno/empresas/{equipe['id']}"
    antes = _painel(cliente, equipe["id"], lider)
    for endpoint in ("decisao", "aprovar"):
        r = cliente.put(base + "/" + endpoint, headers=colega["headers"], json={"preco":100,"rascunho":True,"versao":salva["versao"],"rodada":1}) if endpoint == "decisao" else cliente.post(base+"/aprovar",headers=colega["headers"],json={"versao":salva["versao"],"rodada":1})
        assert r.status_code == 403
    assert _painel(cliente,equipe["id"],lider) == antes
    assert _painel(cliente,equipe["id"],colega)["equipe"]["pode_decidir"] is False
    assert cliente.post(base+"/previsao",headers=colega["headers"],json={"preco":95,"rodada":1,"rascunho":True}).status_code == 200
    assert _fechar(cliente,equipe,professor).status_code == 422
    _aprovar(cliente,equipe,lider,salva["versao"])
    assert _fechar(cliente,equipe,professor).status_code == 200
    assert _painel(cliente,equipe["id"],colega)["resultados"]


def test_rascunho_incompleto_e_envio_com_pendencias(cliente, professor, equipe):
    lider = equipe["alunos"][0]
    base = f"/api/aluno/empresas/{equipe['id']}"
    r = cliente.put(base+"/decisao",headers=lider["headers"],json={"preco":100,"rodada":1,"versao":0,"rascunho":True})
    assert r.status_code == 200 and r.json()["enviada_em"] is None
    final = cliente.post(base+"/aprovar",headers=lider["headers"],json={"versao":1,"rodada":1})
    assert final.status_code == 422
    assert "Finanças" in final.json()["detail"] and "análise financeira" in final.json()["detail"]
    assert _painel(cliente,equipe["id"],lider)["decisao_atual"]["enviada_em"] is None
    assert _fechar(cliente,equipe,professor).status_code == 422
    enviada = _salvar(cliente,equipe,rascunho=False)
    assert enviada["enviada_em"]
    assert _fechar(cliente,equipe,professor).status_code == 200


def test_transferencia_so_vale_na_proxima_rodada(cliente, professor, equipe):
    lider, proximo, terceiro = equipe["alunos"]
    base = f"/api/aluno/empresas/{equipe['id']}"
    r=cliente.post(base+"/lider",headers=lider["headers"],json={"aluno_id":proximo["id"],"rodada":1})
    assert r.status_code==200
    assert r.json()["lider_id"]==lider["id"] and r.json()["transferencia_rodada"]==2
    assert cliente.post(base+"/lider",headers=lider["headers"],json={"aluno_id":terceiro["id"],"rodada":1}).status_code==409
    assert cliente.put(base+"/decisao",headers=proximo["headers"],json={"preco":100,"rodada":1,"versao":0,"rascunho":True}).status_code==403
    _salvar(cliente,equipe,rascunho=False)
    assert _fechar(cliente,equipe,professor).status_code==200
    painel=_painel(cliente,equipe["id"],proximo)
    assert painel["equipe"]["lider_id"]==proximo["id"] and painel["equipe"]["proximo_lider_id"] is None
    assert cliente.put(base+"/decisao",headers=lider["headers"],json={"preco":100,"rodada":2,"versao":0,"rascunho":True}).status_code==403
    _salvar(cliente,equipe,aluno=proximo,rascunho=False)
    assert _fechar(cliente,equipe,professor).status_code==200
    relatorio=cliente.get(f"/api/professor/turmas/{equipe['turma']['id']}/relatorio-pedagogico",headers=professor)
    # A auditoria registra quem enviou cada versão; não exige assinatura dos colegas.
    assert [r["rodada"] for r in _painel(cliente,equipe["id"],proximo)["resultados"]]==[1,2]


def test_versao_e_rodada_impedem_sobrescrita(cliente, equipe):
    lider=equipe["alunos"][0]
    salva=_salvar(cliente,equipe)
    base=f"/api/aluno/empresas/{equipe['id']}/decisao"
    antes=_painel(cliente,equipe["id"],lider)
    assert cliente.put(base,headers=lider["headers"],json={"preco":90,"rodada":1,"rascunho":True}).status_code==422
    assert cliente.put(base,headers=lider["headers"],json={"preco":90,"rodada":1,"versao":0,"rascunho":True}).status_code==409
    assert cliente.put(base,headers=lider["headers"],json={"preco":90,"rodada":2,"versao":salva["versao"],"rascunho":True}).status_code==409
    assert _painel(cliente,equipe["id"],lider)==antes


def test_minimo_tres_e_maximo_cinco(cliente, professor):
    equipe=_criar_equipe(cliente,professor,quantidade=2)
    aluno=equipe["alunos"][0]
    base=f"/api/aluno/empresas/{equipe['id']}"
    assert cliente.post(base+"/lider",headers=aluno["headers"],json={"aluno_id":aluno["id"],"rodada":1}).status_code==422
    assert _fechar(cliente,equipe,professor).status_code==422
    for i in (2,3,4):
        a=_aluno(cliente,i)
        assert cliente.post("/api/aluno/equipes/entrar",headers=a["headers"],json={"empresa_id":equipe["id"]}).status_code==201
    sexto=_aluno(cliente,5)
    assert cliente.post("/api/aluno/equipes/entrar",headers=sexto["headers"],json={"empresa_id":equipe["id"]}).status_code==422


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


def test_envio_sem_rascunho_informa_pendencia(cliente, equipe):
    lider = equipe["alunos"][0]
    resposta = cliente.post(f"/api/aluno/empresas/{equipe['id']}/aprovar", headers=lider["headers"], json={"versao":1,"rodada":1})
    assert resposta.status_code == 422
    assert "rascunho" in resposta.json()["detail"]
