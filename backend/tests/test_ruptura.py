"""Resposta do consumidor à falta do produto (aprovada em 18/11/2026)."""
from types import SimpleNamespace

from app.motor.portfolio import vender_com_ruptura, classe_ruptura, RESPOSTA_RUPTURA


def _item(pid, preco=10.0):
    return {'produto_id': pid, 'produto_nome': pid, 'preco': preco, 'canais': ['DIRETO'], 'peso': 1}


def _estado(**estoques):
    return {'estoque_mp': {'quantidade': 0, 'valor': 0}, 'estoque_pa': {'quantidade': 0, 'valor': 0},
            'estoques_produtos': {pid: {'estoque_mp': {'quantidade': 0, 'valor': 0},
                                        'estoque_pa': {'quantidade': q, 'valor': q * 5.0}}
                                  for pid, q in estoques.items()}}


def test_classes_do_catalogo():
    assert classe_ruptura('pet-racao-umida-em-sache') == 'CONSUMO'
    assert classe_ruptura('pet-areia-sanitaria') == 'CONSUMO'
    assert classe_ruptura('pet-caminha') == 'DURAVEL'
    assert classe_ruptura('pet-brinquedo') == 'DURAVEL'
    assert classe_ruptura('colchoes-colchao-de-espuma-d23-solteiro') == 'DURAVEL'
    assert classe_ruptura('inexistente') is None
    assert sum(RESPOSTA_RUPTURA['CONSUMO'].values()) == 1
    assert sum(RESPOSTA_RUPTURA['DURAVEL'].values()) == 1


def test_consumo_substitui_na_loja_transfere_e_adia():
    # Sachê sem estoque; petisco (mesma linha Alimentação) com estoque.
    itens = [_item('pet-racao-umida-em-sache'), _item('pet-petisco')]
    estado = _estado(**{'pet-racao-umida-em-sache': 0, 'pet-petisco': 200})
    linhas, r = vender_com_ruptura(estado, itens, 200, [1, 1])
    # 100 clientes sem sachê: 45 substituem, 31 vão a outra loja, 15 adiam, 9 desistem.
    assert r['substituidas'] == 45
    assert r['outra_loja'] == {'pet-racao-umida-em-sache': 31}
    assert r['pendentes'] == {'pet-racao-umida-em-sache': 15}
    assert r['perdidas'] == 9
    assert linhas[1]['vendas'] == 145 and linhas[1]['substituicoes'] == 45
    assert estado['estoques_produtos']['pet-petisco']['estoque_pa']['quantidade'] == 55


def test_duravel_vira_pedido_pendente_e_e_atendido_primeiro():
    itens = [_item('pet-caminha')]
    estado = _estado(**{'pet-caminha': 50})
    linhas, r = vender_com_ruptura(estado, itens, 100, [1])
    assert r['pendentes'] == {'pet-caminha': 31} and r['perdidas'] == 19
    assert not r['outra_loja'] and r['substituidas'] == 0
    # Mês seguinte: chega estoque; pendentes têm prioridade.
    estado['estoques_produtos']['pet-caminha']['estoque_pa'] = {'quantidade': 40, 'valor': 200.0}
    linhas, r = vender_com_ruptura(estado, itens, 20, [1], pendentes=r['pendentes'])
    assert r['pendentes_atendidos'] == 31 and linhas[0]['vendas'] == 40
    # 11 clientes novos sem produto: 62% pendentes (7) e 38% perdidos (4).
    assert r['pendentes'] == {'pet-caminha': 7} and r['perdidas'] == 4


def test_pendente_nao_atendido_de_novo_e_perdido_e_transferidos_por_ultimo():
    itens = [_item('pet-caminha')]
    estado = _estado(**{'pet-caminha': 5})
    linhas, r = vender_com_ruptura(estado, itens, 0, [1], pendentes={'pet-caminha': 8},
                                   transferidas={'pet-caminha': 3})
    assert r['pendentes_atendidos'] == 5 and r['pendentes_perdidos'] == 3
    assert r['transferidas_atendidas'] == 0 and r['transferidas_perdidas'] == 3
    assert r['pendentes'] == {}


def test_extras_limitados_pela_capacidade_de_entrega():
    itens = [_item('pet-caminha')]
    estado = _estado(**{'pet-caminha': 100})
    linhas, r = vender_com_ruptura(estado, itens, 10, [1], pendentes={'pet-caminha': 8},
                                   transferidas={'pet-caminha': 8}, limite_extra=10)
    assert linhas[0]['pendentes_recebidos'] == 8 and linhas[0]['transferidas_recebidas'] == 2


def test_vestuario_perde_a_venda():
    from app.catalogo_fixo import catalogo
    pid = catalogo('vestuario')[0]['id']
    estado = _estado(**{pid: 0})
    _, r = vender_com_ruptura(estado, [_item(pid)], 10, [1])
    assert r['perdidas'] == 10 and not r['pendentes'] and not r['outra_loja']


def test_modelo_basico_troca_de_loja_so_no_consumo():
    from app.motor.simulacao import _fracao_troca_de_loja
    def calc(*pids):
        itens = [{'produto_id': p, 'preco_mercado': 10, 'peso': 1} for p in pids]
        return SimpleNamespace(decisao=SimpleNamespace(plano_comercial={'produtos': itens}))
    assert _fracao_troca_de_loja(calc('pet-caminha')) == 0
    assert abs(_fracao_troca_de_loja(calc('pet-petisco', 'pet-caminha')) - .155) < 1e-9


def test_clientes_trocam_para_lojas_que_vendem_o_produto(monkeypatch):
    from app.motor import avancado
    previas = [{'transferencias_ruptura': {'pet-petisco': 30}}, {'transferencias_ruptura': {}},
               {'transferencias_ruptura': {}}]
    fila = iter(previas)
    monkeypatch.setattr(avancado, 'motor', lambda turma: SimpleNamespace(apurar=lambda p, d, t: next(fila)))
    def prep(pids, atr=1.0):
        itens = [{'produto_id': p, 'preco_mercado': 20} for p in pids]
        return {'decisao': {'plano_comercial': {'produtos': itens}}, 'parametros': {},
                'atratividade': atr, 'comercial_ativo': True}
    preparos = [prep(['pet-petisco']), prep(['pet-petisco'], 2.0), prep(['pet-caminha'], 5.0)]
    bots = [{'atratividade': 1.0, 'preco': 100, 'receita': 0.0, 'capacidade': 10_000}]
    turma = SimpleNamespace(preco_referencia=100)
    avancado._transferir_ruptura(turma, preparos, [0, 0, 0], bots)
    # Loja 3 não vende petisco; 30 clientes se dividem 2:1 entre a loja 2 e o concorrente.
    assert preparos[1]['parametros']['demanda_transferida'] == {'pet-petisco': 20}
    assert 'demanda_transferida' not in preparos[2]['parametros']
    assert bots[0]['receita'] == 200.0 and bots[0]['clientes_recebidos_ruptura'] == 10
