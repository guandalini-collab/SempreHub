from app import config


def test_proprietario_gerencia_docentes_sem_liberar_acesso_ao_aluno(cliente, professor, monkeypatch):
    monkeypatch.setattr(config, 'PROPRIETARIOS', ['prof@iffarroupilha.edu.br'])
    login = cliente.post('/api/auth/login', json={'email':'prof@iffarroupilha.edu.br','senha':'senha-segura'})
    assert login.status_code == 200
    assert login.json()['usuario']['papel'] == 'PROPRIETARIO'
    dono = {'Authorization': f"Bearer {login.json()['token']}"}
    criado = cliente.post('/api/professor/proprietario/professores', headers=dono, json={
        'nome':'Professora Convidada', 'email':'convidada@iffar.edu.br', 'senha_provisoria':'senha-segura',
    })
    assert criado.status_code == 201, criado.text
    assert cliente.get('/api/professor/proprietario/professores', headers=dono).json()[0]['email'] == 'convidada@iffar.edu.br'
