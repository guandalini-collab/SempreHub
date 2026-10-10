import pytest
from app.motor.indicadores import otif
from app.motor.tradicional import preparar, apurar
from tests.test_tradicional import base, sem_tributos
from tests import test_tradicional as contabil


def test_exemplo_quinze_pedidos():
    r = otif(15, 15, 'ECONOMICO')
    assert r['pedidos_com_falha'] == 2
    assert r['pedidos_perfeitos'] == 13
    assert r['otif'] == pytest.approx(13/15)


@pytest.mark.parametrize('modal,taxa', [('ECONOMICO', .125), ('PADRAO', .054), ('RAPIDO', .01)])
def test_contagens_conciliadas_sem_dupla_penalizacao(modal, taxa):
    for total in range(301):
        r = otif(total, total//2, modal)
        assert all(isinstance(v, int) for k,v in r.items() if k.startswith('pedidos_'))
        assert r['pedidos_perfeitos'] + r['pedidos_com_falha'] == total
        assert r['pedidos_com_falha'] == r['pedidos_atrasados'] + r['pedidos_incompletos'] - r['pedidos_falha_dupla'] + r['pedidos_falhas_gerais']
        assert r['pedidos_falha_dupla'] <= min(r['pedidos_atrasados'], r['pedidos_incompletos_transporte'])
        assert r['taxa_falha_transporte'] == taxa
        assert r['otif'] is None if total == 0 else 0 <= r['otif'] <= 1


def test_empate_arredonda_para_cima():
    assert otif(4,4,'ECONOMICO')['pedidos_com_falha'] == 1
    assert otif(50,50,'RAPIDO')['pedidos_com_falha'] == 1


def test_ruptura_nao_recebe_falha_de_transporte():
    r = otif(100, 80, 'ECONOMICO')
    assert r['pedidos_nao_atendidos'] == 20
    assert r['pedidos_com_falha'] == 30
    assert r['pedidos_perfeitos'] == 70
    assert otif(100,0,'RAPIDO')['otif'] == 0
    assert otif(0,10,'PADRAO')['otif'] is None
    assert otif(10,20,'PADRAO')['pedidos_despachados'] == 10


def test_premium_falha_geral_sem_inventar_atrasos():
    r = otif(100,100,'RAPIDO')
    assert r['pedidos_falhas_gerais'] == 1
    assert r['pedidos_atrasados'] == r['pedidos_incompletos'] == 0
    assert r['otif'] == .99


def test_satisfacao_usa_mesmas_falhas_sem_alterar_contabilidade():
    e,d,p = base()
    d['simulacao']['modal'] = 'ECONOMICO'
    r = apurar(preparar(e,d,p,1), 100, sem_tributos)
    op = r['detalhes']['operacao']
    taxa = (op['pedidos_com_falha'] - op['pedidos_nao_atendidos']) / r['vendas']
    esperado = 80 + 2 - 30*taxa - 20*op['ruptura']/100
    assert r['satisfacao'] == pytest.approx(esperado)
    contabil.TestTradicional().assert_reconciliacao(e,r)
