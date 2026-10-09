from .decisoes import completar_decisao
from types import SimpleNamespace as S
from app.experiencia import jornada_empresa
from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar


def resultado(rodada, lucro, participacao):
    return S(rodada=rodada, lucro_liquido=lucro, participacao_mercado=participacao)


def test_sem_historico_nao_inventa_conquistas_ou_feed():
    jornada = jornada_empresa(S(resultados=[], decisoes=[]))
    assert jornada['rodadas_concluidas'] == 0
    assert jornada['feed'] == []
    assert not any(c['obtida'] for c in jornada['conquistas'])


def test_decisao_automatica_nao_recebe_conquista_de_envio():
    jornada = jornada_empresa(S(resultados=[], decisoes=[S(rodada=1, automatica=True)]))
    assert not jornada['conquistas'][0]['obtida']


def test_marcos_preservam_primeira_ocorrencia_e_feed_ordena_historico():
    empresa = S(resultados=[resultado(3, 500, .3), resultado(1, -20, .1), resultado(2, 200, .2)], decisoes=[S(rodada=2, automatica=False)])
    jornada = jornada_empresa(empresa)
    marcos = {c['id']: c['rodada'] for c in jornada['conquistas']}
    assert marcos == {'primeiro-movimento': 2, 'empresa-em-acao': 1, 'resultado-positivo': 2, 'virada': 2, 'presenca': 2}
    assert [f['rodada'] for f in jornada['feed']] == [3, 2, 1]
    assert jornada['feed'][0]['lucro'] == 500
    assert [r.rodada for r in empresa.resultados] == [3, 1, 2]


def test_painel_entrega_jornada_e_isola_empresas(cliente, professor):
    turma = _criar_turma(cliente, professor)
    aluno = cadastrar(cliente, 'UX aluno', 'ux@aluno.iffar.edu.br')
    outro = cadastrar(cliente, 'Outro', 'outro-ux@aluno.iffar.edu.br')
    id = _entrar(cliente, aluno, turma['codigo'], 'Empresa UX')
    url = f'/api/aluno/empresas/{id}'
    assert cliente.get(url, headers=outro).status_code == 404
    assert cliente.get(url, headers=aluno).json()['jornada']['rodadas_concluidas'] == 0
    assert cliente.put(f'{url}/decisao', headers=aluno, json=completar_decisao({'preco': 95})).status_code == 200
    conquista = cliente.get(url, headers=aluno).json()['jornada']['conquistas'][0]
    assert conquista['obtida'] and conquista['rodada'] == 1
