import json
from copy import deepcopy

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.database import SessionLocal
from app.manutencao_turma_teste import converter
from app.models import Turma
from app.schemas import DecisaoSimulacao
from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar
from .test_avancado_api import _fechar


def test_maquinas_bloqueadas_ate_mes_tres_e_estudo_persistido(cliente, professor):
    turma = _criar_turma(cliente, professor, modo_jogo="TRADICIONAL", total_rodadas=4)
    aluno = cadastrar(cliente, "Ana", "cg@aluno.iffar.edu.br")
    empresa = _entrar(cliente, aluno, turma["codigo"], "Fábrica")
    base = {"preco": 100, "simulacao": {"comprar_maquinas": 1}}
    for rodada in (1, 2):
        for rota in ('previsao', 'decisao'):
            resposta = getattr(cliente, 'post' if rota == 'previsao' else 'put')(f'/api/aluno/empresas/{empresa}/{rota}', headers=aluno, json={**base, 'rodada': rodada})
            assert resposta.status_code == 422
            assert 'terceiro mês' in resposta.json()['detail']
        _fechar(cliente, professor, turma, rodada)
    estudo = {"pontos": [{"nome": "A", "x": -10, "y": 20, "volume": 10}, {"nome": "B", "x": 30, "y": 60, "volume": 30}], "local_x": 20, "local_y": 50, "justificativa": "Acesso rodoviário"}
    resposta = cliente.put(f'/api/aluno/empresas/{empresa}/decisao', headers=aluno, json={**base, 'rodada': 3, 'simulacao': {"comprar_maquinas": 1, "centro_gravidade": estudo}})
    assert resposta.status_code == 200, resposta.text
    painel = cliente.get(f'/api/aluno/empresas/{empresa}', headers=aluno).json()
    assert painel['decisao_atual']['simulacao']['centro_gravidade'] == estudo
    _fechar(cliente, professor, turma, 3)
    painel = cliente.get(f'/api/aluno/empresas/{empresa}', headers=aluno).json()
    maquinas = painel['empresa']['estado_simulacao']['maquinas']
    assert maquinas[-1]['ativacao'] == 4


def test_estudo_rejeita_pesos_negativos_e_coordenadas_invalidas():
    for ponto in ({'volume': -1}, {'x': float('nan')}, {'y': float('inf')}):
        with pytest.raises(ValidationError):
            DecisaoSimulacao(centro_gravidade={'pontos': [ponto]})
    with pytest.raises(ValidationError):
        DecisaoSimulacao(centro_gravidade={'pontos': [{}] * 21})


def test_conversao_apenas_turma_de_teste_e_preserva_historico(cliente, professor):
    turma = _criar_turma(cliente, professor, nome='Turma Teste', total_rodadas=4)
    aluno = cadastrar(cliente, "Ana", "migracao@aluno.iffar.edu.br")
    empresa = _entrar(cliente, aluno, turma['codigo'], 'Fábrica')
    _fechar(cliente, professor, turma, 1)
    cliente.put(f'/api/aluno/empresas/{empresa}/decisao', headers=aluno, json={'preco': 120})
    antes = cliente.get(f'/api/aluno/empresas/{empresa}', headers=aluno).json()
    with SessionLocal.begin() as db:
        with pytest.raises(ValueError):
            converter(db)
        db.get(Turma, turma['id']).codigo = 'GS9VFD'
    with SessionLocal.begin() as db:
        converter(db)
    depois = cliente.get(f'/api/aluno/empresas/{empresa}', headers=aluno).json()
    assert depois['turma']['modo_jogo'] == 'TRADICIONAL'
    assert depois['resultados'] == antes['resultados']
    assert depois['empresa']['caixa'] == antes['empresa']['caixa']
    assert depois['empresa']['divida'] == antes['empresa']['divida']
    assert depois['empresa']['estado_simulacao']['maquinas']
    assert depois['decisao_atual']['enviada_em'] is None
    with SessionLocal.begin() as db:
        assert 'já está' in converter(db)
        backup = json.loads(db.execute(text('SELECT dados FROM semprehub_manutencao_backup')).scalar_one())
        assert backup['turma']['modo_jogo'] == 'LEGADO'
        db.execute(text('DROP TABLE semprehub_manutencao_backup'))
