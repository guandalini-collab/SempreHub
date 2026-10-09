from .conftest import cadastrar
from .test_fluxo import _criar_turma
from .test_equipes import _criar_equipe, _aluno


def test_turma_por_nome_visibilidade_e_trava_global(cliente,professor):
    turma=_criar_turma(cliente,professor,nome="A",modo_equipe=True)
    outra=_criar_turma(cliente,professor,nome="Marketing noturno",modo_equipe=True)
    aluno=cadastrar(cliente,"Ana","nome@aluno.iffar.edu.br")
    assert {t["nome"] for t in cliente.get("/api/aluno/turmas",headers=aluno).json()}=={"A","Marketing noturno"}
    url=f"/api/professor/turmas/{outra['id']}"
    assert cliente.put(url+"/ingresso",headers=professor,json={"visivel_ingresso":False,"formacao_encerrada":False}).status_code==200
    assert len(cliente.get("/api/aluno/turmas",headers=aluno).json())==1
    assert cliente.post("/api/aluno/matricula",headers=aluno,json={"turma_id":outra["id"]}).status_code==422
    assert cliente.post("/api/aluno/matricula",headers=aluno,json={"turma_id":turma["id"]}).status_code==200
    assert cliente.put(url+"/ingresso",headers=professor,json={"visivel_ingresso":True,"formacao_encerrada":False}).status_code==200
    assert cliente.post("/api/aluno/matricula",headers=aluno,json={"turma_id":outra["id"]}).status_code==403
    uid=cliente.get("/api/auth/eu",headers=aluno).json()["id"]
    destino=f"/api/professor/turmas/{turma['id']}/autorizar-troca"
    assert cliente.post(destino,headers=aluno,json={"aluno_id":uid,"destino_id":outra["id"],"motivo":"Correção de matrícula"}).status_code==403
    assert cliente.post(destino,headers=professor,json={"aluno_id":uid,"destino_id":outra["id"],"motivo":"Correção de matrícula"}).status_code==200
    assert cliente.post("/api/aluno/matricula",headers=aluno,json={"turma_id":outra["id"]}).status_code==200
    assert cliente.post("/api/aluno/matricula",headers=aluno,json={"turma_id":turma["id"]}).status_code==403


def test_professor_distribui_somente_cadastrados_e_respeita_limites(cliente,professor):
    equipe=_criar_equipe(cliente,professor)
    for i in (10,11):
        a=_aluno(cliente,i)
        assert cliente.post("/api/aluno/matricula",headers=a["headers"],json={"turma_id":equipe["turma"]["id"]}).status_code==200
    url=f"/api/professor/turmas/{equipe['turma']['id']}"
    sala=cliente.get(url+"/formacao",headers=professor).json()
    assert len(sala["disponiveis"])==2 and len(sala["equipes"][0]["membros"])==3
    r=cliente.post(url+"/distribuir-sem-equipe",headers=professor,json={})
    assert r.status_code==200 and len(r.json()["distribuicao"])==2
    sala=cliente.get(url+"/formacao",headers=professor).json()
    assert not sala["disponiveis"] and len(sala["equipes"][0]["membros"])==5
    assert sala["formacao_encerrada"]


def test_sem_vagas_nao_distribui_parcialmente(cliente,professor):
    equipe=_criar_equipe(cliente,professor,quantidade=2)
    a=_aluno(cliente,10)
    cliente.post("/api/aluno/matricula",headers=a["headers"],json={"turma_id":equipe["turma"]["id"]})
    url=f"/api/professor/turmas/{equipe['turma']['id']}"
    antes=cliente.get(url+"/formacao",headers=professor).json()
    r=cliente.post(url+"/distribuir-sem-equipe",headers=professor,json={})
    assert r.status_code==422 and "pelo menos 3" in r.json()["detail"]
    assert cliente.get(url+"/formacao",headers=professor).json()==antes


def test_equipes_por_afinidade_e_lider_escolhido_pela_maioria(cliente,professor):
    turma=_criar_turma(cliente,professor,modo_equipe=True)
    alunos=[_aluno(cliente,i) for i in range(3)]
    for a in alunos:cliente.post("/api/aluno/matricula",headers=a["headers"],json={"turma_id":turma["id"]})
    r=cliente.post("/api/aluno/turmas/entrar",headers=alunos[0]["headers"],json={"turma_id":turma["id"],"nome_empresa":"Afinidade","tipo_entrada_gem":"OPORTUNIDADE","classe_dornelas":"SERIAL"})
    eid=r.json()["empresa"]["id"]
    for a in alunos[1:]:assert cliente.post("/api/aluno/equipes/entrar",headers=a["headers"],json={"empresa_id":eid}).status_code==201
    url=f"/api/aluno/empresas/{eid}"
    assert cliente.get(url,headers=alunos[0]["headers"]).json()["equipe"]["lider_id"] is None
    for i in (0,2):
        r=cliente.post(url+"/lider",headers=alunos[i]["headers"],json={"aluno_id":alunos[1]["id"],"rodada":1})
        assert r.status_code==200
    assert r.json()["lider_id"]==alunos[1]["id"]
    assert not cliente.get(url,headers=alunos[0]["headers"]).json()["equipe"]["pode_decidir"]
