from .decisoes import completar_decisao
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
    resposta = cliente.put(f'/api/aluno/empresas/{empresa}/decisao', headers=aluno, json=completar_decisao({**base, 'rodada': 3, 'simulacao': {"comprar_maquinas": 1, "centro_gravidade": estudo}}))
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
    cliente.put(f'/api/aluno/empresas/{empresa}/decisao', headers=aluno, json=completar_decisao({'preco': 120}))
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


def test_localizacao_altera_previa_dre_e_preserva_balanco(cliente, professor):
    turma = _criar_turma(cliente, professor, modo_jogo="TRADICIONAL", total_rodadas=2, demanda_base_por_empresa=40, configuracao_simulacao={"custo_frete_km": .5})
    aluno = cadastrar(cliente, "Ana", "frete@aluno.iffar.edu.br")
    empresa = _entrar(cliente, aluno, turma["codigo"], "Fábrica")
    base = f"/api/aluno/empresas/{empresa}"
    estudo = {"pontos": [{"nome": "A", "x": 0, "y": 0, "volume": 1}, {"nome": "B", "x": 40, "y": 0, "volume": 3}], "local_x": 0, "local_y": 0}
    revisao = {k: True for k in ("decisoes", "financas", "producao", "logistica")}
    decisao = {"rodada": 1, "preco": 100, "revisao_areas": revisao, "simulacao": {"comprar_mp": 100, "producao": 100, "centro_gravidade": estudo}}
    previa = cliente.post(base + "/previsao", headers=aluno, json=decisao)
    assert previa.status_code == 200, previa.text
    assert previa.json()["simulacao"]["frete_unitario"] == 25
    assert cliente.put(base + "/decisao", headers=aluno, json=completar_decisao(decisao)).status_code == 200
    assert cliente.get(base, headers=aluno).json()["decisao_atual"]["revisao_areas"] == revisao
    _fechar(cliente, professor, turma, 1)
    resultado = cliente.get(base, headers=aluno).json()["resultados"][0]
    operacao = resultado["detalhes_simulacao"]["operacao"]
    assert operacao["distancia_media_km"] == 30
    assert operacao["frete_unitario"] == 25
    assert resultado["unidades_vendidas"] > 0
    assert resultado["dre"]["frete"] == resultado["unidades_vendidas"] * 25
    balanco = resultado["detalhes_simulacao"]["balanco"]
    ativo = sum(balanco[k] for k in ("caixa", "receber", "estoques", "imobilizado"))
    assert abs(ativo - balanco["pagar"] - balanco["divida"] - balanco["patrimonio"]) < .01
    _fechar(cliente, professor, turma, 2)
    assert cliente.get(base, headers=aluno).json()["resultados"][0] == resultado


def test_frete_sem_localizacao_mantem_tarifa_e_nao_muta_estudo():
    from app.motor.localizacao import estimar_frete
    estudo = {"modal": "ECONOMICO", "centro_gravidade": {"pontos": [{"x": 0, "y": 0, "volume": 0}], "local_x": 100, "local_y": 100}}
    antes = deepcopy(estudo)
    resultado = estimar_frete(estudo, {})
    assert resultado["frete_unitario"] == 5
    assert resultado["localizacao_aplicada"] is False
    assert estudo == antes
