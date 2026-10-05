"""Testes puros: também podem rodar com ``python -m unittest tests.test_tradicional``."""

from copy import deepcopy
import unittest

from app.motor.tradicional import apurar, preparar


def base():
    empresa = {
        "caixa": 20000.0, "divida": 0.0, "funcionarios": 0,
        "autoeficacia": 60, "regime_tributario": "SIMPLES_NACIONAL",
        "classe_dornelas": "SERIAL", "marca": 0, "qualidade": 0,
        "estado_simulacao": {
            "versao": 1, "estoque_mp": {"quantidade": 0, "valor": 0.0},
            "estoque_pa": {"quantidade": 0, "valor": 0.0},
            "estoque_obsoleto": {"quantidade": 0, "valor": 0.0},
            "maquinas": [{"custo": 0.0, "valor_liquido": 0.0, "capacidade": 240,
                          "condicao": 1.0, "ativacao": 1, "vida_util": 24}],
            "receber": [], "pagar": [],
            "rh": {"moral": 100.0, "qualificacao": 0.0, "rotatividade_acumulada": 0.0},
            "satisfacao": 80.0, "clientes": 0,
            "participacao_fundadores": 1.0, "capital_aportado": 0.0,
        },
    }
    parametros = {
        "custo_unitario": 40.0, "produtividade_por_pessoa": 120.0,
        "custos_fixos_mensais": 0.0, "salario_base": 0.0,
        "taxa_juros_mensal": 0.0, "taxa_cheque_especial": 0.08,
        "limite_credito": 50000.0, "preco_referencia": 100.0,
        "configuracao_simulacao": {
            "custo_armazenagem": 0.0, "frete_padrao": 0.0,
            "frete_rapido": 0.0, "frete_economico": 0.0,
            "preco_maquina": 12000.0, "capacidade_maquina": 240,
            "vida_util_maquina": 24,
        },
    }
    decisao = {"preco": 100.0, "simulacao": {"producao": 100, "comprar_mp": 100}}
    return empresa, decisao, parametros


def sem_tributos(receita, cmv):
    return 0.0, 0.0


def proxima_empresa(empresa, resultado):
    nova = deepcopy(empresa)
    nova.update(estado_simulacao=deepcopy(resultado["estado"]), caixa=resultado["caixa"],
                divida=resultado["divida"], funcionarios=resultado["funcionarios"],
                marca=resultado["marca"], qualidade=resultado["qualidade"])
    return nova


def patrimonio_inicial(empresa):
    s = empresa["estado_simulacao"]
    return (empresa["caixa"] - empresa["divida"]
            + sum(t["valor"] for t in s["receber"])
            - sum(t["valor"] for t in s["pagar"])
            + sum(s[n]["valor"] for n in ("estoque_mp", "estoque_pa", "estoque_obsoleto"))
            + sum(m["valor_liquido"] for m in s["maquinas"]))


class TestTradicional(unittest.TestCase):
    def assert_reconciliacao(self, empresa, resultado):
        dfc, balanco = resultado["detalhes"]["dfc"], resultado["detalhes"]["balanco"]
        self.assertAlmostEqual(dfc["caixa_inicial"] + dfc["variacao"], resultado["caixa"], places=2)
        self.assertAlmostEqual(dfc["operacional"] + dfc["investimento"] + dfc["financiamento"], dfc["variacao"], places=2)
        self.assertAlmostEqual(balanco["caixa"] + balanco["receber"] + balanco["estoques"]
                               + balanco["imobilizado"] - balanco["pagar"] - balanco["divida"],
                               balanco["patrimonio"], places=2)
        self.assertAlmostEqual(patrimonio_inicial(empresa) + resultado["dre"]["lucro_liquido"],
                               balanco["patrimonio"], places=2)

    def test_estoque_lucro_caixa_e_venda_na_rodada_seguinte(self):
        empresa, decisao, parametros = base()
        primeiro = apurar(preparar(empresa, decisao, parametros, 1), 40, sem_tributos)
        self.assertEqual(primeiro["dre"]["lucro_liquido"], 2400)
        self.assertEqual(primeiro["detalhes"]["dfc"]["variacao"], 0)
        self.assertEqual(primeiro["estado"]["estoque_pa"], {"quantidade": 60, "valor": 2400.0})
        self.assert_reconciliacao(empresa, primeiro)
        fotografia_primeiro = deepcopy(primeiro)
        segunda_empresa = proxima_empresa(empresa, primeiro)
        segundo = apurar(preparar(segunda_empresa, {"preco": 100, "simulacao": {}}, parametros, 2), 60, sem_tributos)
        self.assertEqual(segundo["dre"]["lucro_liquido"], 3600)
        self.assertEqual(segundo["detalhes"]["dfc"]["variacao"], 6000)
        self.assertEqual(segundo["estado"]["estoque_pa"], {"quantidade": 0, "valor": 0.0})
        self.assertEqual(segundo["detalhes"]["estado_inicial"], primeiro["estado"])
        self.assertEqual(primeiro, fotografia_primeiro)
        self.assert_reconciliacao(segunda_empresa, segundo)

    def test_credito_receita_agora_caixa_no_vencimento(self):
        empresa, decisao, parametros = base()
        decisao["simulacao"].update(vendas_prazo=1, compras_prazo=1,
                                   prazo_recebimento=2, prazo_pagamento=1)
        primeiro = apurar(preparar(empresa, decisao, parametros, 1), 40, sem_tributos)
        self.assertEqual(primeiro["dre"]["receita"], 4000)
        self.assertEqual(primeiro["caixa"], 20000)
        self.assertEqual(primeiro["estado"]["receber"], [{"origem": 1, "vencimento": 3, "valor": 4000.0}])
        self.assertEqual(primeiro["estado"]["pagar"], [{"origem": 1, "vencimento": 2, "valor": 4000.0}])
        self.assert_reconciliacao(empresa, primeiro)
        empresa2 = proxima_empresa(empresa, primeiro)
        segundo = apurar(preparar(empresa2, {"preco": 100}, parametros, 2), 0, sem_tributos)
        self.assertEqual(segundo["caixa"], 16000)
        self.assertEqual(segundo["dre"]["receita"], 0)
        self.assertEqual(segundo["estado"]["pagar"], [])
        self.assert_reconciliacao(empresa2, segundo)
        empresa3 = proxima_empresa(empresa2, segundo)
        terceiro = apurar(preparar(empresa3, {"preco": 100}, parametros, 3), 0, sem_tributos)
        self.assertEqual(terceiro["caixa"], 20000)
        self.assertEqual(terceiro["dre"]["receita"], 0)
        self.assertEqual(terceiro["estado"]["receber"], [])
        self.assert_reconciliacao(empresa3, terceiro)

    def test_maquina_e_investimento_ativa_no_proximo_mes(self):
        empresa, decisao, parametros = base()
        empresa["estado_simulacao"]["maquinas"] = []
        decisao["simulacao"]["comprar_maquinas"] = 1
        primeiro = apurar(preparar(empresa, decisao, parametros, 1), 100, sem_tributos)
        self.assertEqual(primeiro["vendas"], 0)
        self.assertEqual(primeiro["dre"]["depreciacao"], 0)
        self.assertEqual(primeiro["detalhes"]["dfc"]["investimento"], -12000)
        self.assertEqual(primeiro["estado"]["maquinas"][0]["ativacao"], 2)
        self.assert_reconciliacao(empresa, primeiro)
        empresa2 = proxima_empresa(empresa, primeiro)
        segundo = apurar(preparar(empresa2, {"preco": 100, "simulacao": {"producao": 100}}, parametros, 2), 40, sem_tributos)
        self.assertEqual(segundo["vendas"], 40)
        self.assertEqual(segundo["dre"]["depreciacao"], 500)
        self.assertEqual(segundo["detalhes"]["dfc"]["investimento"], 0)
        self.assert_reconciliacao(empresa2, segundo)

    def test_refugo_insumos_capacidade_e_custo_nao_duplicado(self):
        empresa, decisao, parametros = base()
        empresa["funcionarios"] = 5
        parametros["produtividade_por_pessoa"] = 200
        decisao["simulacao"].update(producao=312, comprar_mp=312)
        preparo = preparar(empresa, decisao, parametros, 1)
        resultado = apurar(preparo, 500, sem_tributos)
        self.assertEqual(preparo["producao_real"], 312)
        self.assertEqual(preparo["refugo"], 46)  # 15% máximo, unidades inteiras.
        self.assertEqual(resultado["vendas"], 266)
        self.assertEqual(resultado["dre"]["cmv"] + resultado["dre"]["refugos"], 312 * 40)
        self.assertEqual(resultado["estado"]["estoque_mp"]["quantidade"], 0)
        self.assert_reconciliacao(empresa, resultado)

    def test_imutabilidade_e_centavos_com_custo_medio(self):
        empresa, decisao, parametros = base()
        empresa["estado_simulacao"]["estoque_mp"] = {"quantidade": 3, "valor": 1.0}
        parametros["custo_unitario"] = 0.335
        decisao["simulacao"].update(comprar_mp=3, producao=5, vendas_prazo=0.333)
        decisao["preco"] = 1.035
        antes = deepcopy((empresa, decisao, parametros))
        preparo = preparar(empresa, decisao, parametros, 1)
        preparo_antes = deepcopy(preparo)
        primeiro = apurar(preparo, 3, lambda receita, cmv: (receita * 0.06, 0.06))
        self.assertEqual((empresa, decisao, parametros), antes)
        self.assertEqual(preparo, preparo_antes)
        self.assertEqual(primeiro, apurar(preparo, 3, lambda receita, cmv: (receita * 0.06, 0.06)))
        self.assertEqual(primeiro["dre"]["receita"], 3.11)  # 3 × 1,035: HALF_UP, sem erro binário.
        self.assert_reconciliacao(empresa, primeiro)
        primeiro["estado"]["estoque_pa"]["valor"] = 999
        self.assertNotEqual(primeiro["detalhes"]["estado_final"]["estoque_pa"]["valor"], 999)

    def test_rh_treinamento_e_turnover_persistem(self):
        empresa, decisao, parametros = base()
        empresa["funcionarios"] = 5
        empresa["estado_simulacao"]["rh"]["moral"] = 20
        empresa["estado_simulacao"]["rh"]["rotatividade_acumulada"] = 0.8
        parametros["salario_base"] = 2000
        decisao["simulacao"].update(salario=2400, beneficio=200, treinamento=1000)
        preparo = preparar(empresa, decisao, parametros, 1)
        self.assertEqual(preparo["turnover"], 1)
        self.assertEqual(preparo["funcionarios"], 4)
        self.assertGreater(preparo["estado"]["rh"]["moral"], 20)
        self.assertGreater(preparo["estado"]["rh"]["qualificacao"], 0)
        self.assertAlmostEqual(preparo["estado"]["rh"]["rotatividade_acumulada"], 0.2)
        resultado = apurar(preparo, 40, sem_tributos)
        self.assertEqual(resultado["dre"]["beneficios"], 800)
        self.assertEqual(resultado["dre"]["treinamento"], 1000)
        self.assert_reconciliacao(empresa, resultado)

    def test_logistica_cobrada_uma_vez_satisfacao_proxima_rodada(self):
        empresa, decisao, parametros = base()
        parametros["configuracao_simulacao"]["frete_economico"] = 5
        decisao["simulacao"]["modal"] = "ECONOMICO"
        preparo = preparar(empresa, decisao, parametros, 1)
        resultado = apurar(preparo, 40, sem_tributos)
        self.assertEqual(resultado["dre"]["frete"], 200)
        self.assertEqual(resultado["detalhes"]["dfc"]["variacao"], -200)
        self.assertEqual(resultado["estado"]["satisfacao"], 76)
        self.assertEqual(preparo["estado"]["satisfacao"], 80)
        empresa2 = proxima_empresa(empresa, resultado)
        baixa = preparar(empresa2, {"preco": 100}, parametros, 2)
        empresa2["estado_simulacao"]["satisfacao"] = 80
        alta = preparar(empresa2, {"preco": 100}, parametros, 2)
        self.assertLess(baixa["atratividade"], alta["atratividade"])
        self.assert_reconciliacao(empresa, resultado)

    def test_canal_comissao_e_marketing_digital_nao_duplicam_orcamento(self):
        empresa, decisao, parametros = base()
        decisao["marketing"] = 100
        decisao["simulacao"].update({"canal": "DISTRIBUIDOR", "marketing_digital": 100})
        resultado = apurar(preparar(empresa, decisao, parametros, 1), 40, sem_tributos)
        self.assertEqual(resultado["dre"]["comissao_canal"], 200)
        self.assertEqual(resultado["detalhes"]["operacao"]["canal"], "DISTRIBUIDOR")
        self.assertEqual(resultado["detalhes"]["operacao"]["marketing_digital"], 100)
        self.assertEqual(resultado["dre"]["marketing"], 100)

    def test_credito_principal_amortizacao_e_vencimento_nao_sao_despesas(self):
        empresa, decisao, parametros = base()
        empresa["divida"] = 1000
        empresa["estado_simulacao"]["vencimento_divida"] = 1
        decisao.update(emprestimo=5000, amortizacao=300)
        decisao["simulacao"] = {}
        parametros["taxa_juros_mensal"] = 0.025
        preparo = preparar(empresa, decisao, parametros, 1)
        self.assertEqual(preparo["amortizacao_obrigatoria"], 700)
        self.assertEqual(preparo["amortizacao"], 1000)
        self.assertEqual(preparo["divida"], 5000)
        resultado = apurar(preparo, 0, sem_tributos)
        self.assertEqual(resultado["dre"]["lucro_liquido"], -125)
        self.assertEqual(resultado["caixa"], 23875)
        self.assertNotIn("vencimento_divida", resultado["estado"])
        self.assert_reconciliacao(empresa, resultado)

    def test_evento_novo_preco_nao_reavalia_estoque_antigo(self):
        empresa, decisao, parametros = base()
        empresa["estado_simulacao"]["estoque_mp"] = {"quantidade": 100, "valor": 4000}
        decisao["simulacao"] = {"producao": 100}
        resultado = apurar(preparar(empresa, decisao, parametros, 1, multiplicador_custo=2), 100, sem_tributos)
        self.assertEqual(resultado["dre"]["cmv"], 4000)
        self.assert_reconciliacao(empresa, resultado)


if __name__ == "__main__":
    unittest.main()
