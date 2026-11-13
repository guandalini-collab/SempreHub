"""Invariantes contábeis do modelo físico com cadeia operacional explícita."""

from copy import deepcopy
import unittest

from app.motor.tradicional import apurar, preparar


def base():
    empresa = {
        "caixa": 50_000.0, "divida": 0.0, "funcionarios": 1,
        "autoeficacia": 60, "regime_tributario": "SIMPLES_NACIONAL",
        "classe_dornelas": "SERIAL", "marca": 0.0, "qualidade": 0.0,
        "estado_simulacao": {
            "versao": 1,
            "estoque_mp": {"quantidade": 0, "valor": 0.0},
            "estoque_pa": {"quantidade": 0, "valor": 0.0},
            "estoque_obsoleto": {"quantidade": 0, "valor": 0.0},
            "maquinas": [{"custo": 12_000.0, "valor_liquido": 12_000.0, "capacidade": 400,
                          "condicao": 1.0, "ativacao": 1, "vida_util": 24}],
            "receber": [], "pagar": [],
            "rh": {"moral": 80.0, "qualificacao": 0.0, "rotatividade_acumulada": 0.0},
            "satisfacao": 80.0, "clientes": 0,
        },
    }
    parametros = {
        "custo_unitario": 40.0, "produtividade_por_pessoa": 120.0,
        "custos_fixos_mensais": 0.0, "salario_base": 2_000.0,
        "taxa_juros_mensal": 0.0, "taxa_cheque_especial": 0.08,
        "limite_credito": 50_000.0, "preco_referencia": 100.0,
        "configuracao_simulacao": {
            "custo_armazenagem": 0.0, "frete_padrao": 5.0,
            "frete_rapido": 8.0, "frete_economico": 3.0,
            "preco_maquina": 12_000.0, "capacidade_maquina": 400,
            "vida_util": 24,
        },
    }
    produto = {
        "produto_id": "p1", "produto_nome": "Produto de teste", "peso": 1,
        "custo_unitario": 40.0, "preco": 100.0, "canais": ["DIRETO"],
        "posicionamento": "PRECO", "midias": [],
    }
    decisao = {
        "preco": 100.0, "marketing": 500.0, "pd": 0.0, "networking": 0.0,
        "contratar": 0, "demitir": 0, "emprestimo": 0.0, "amortizacao": 0.0,
        "plano_comercial": {"produtos": [produto], "custo_unitario": 40.0},
        "simulacao": {"producao": 100, "comprar_mp": 100, "modal": "PADRAO",
                       "orcamento_logistico": 500.0},
    }
    return empresa, decisao, parametros


def sem_tributos(receita, cmv):
    return 0.0, 0.0


def proxima_empresa(empresa, resultado):
    nova = deepcopy(empresa)
    nova.update(estado_simulacao=deepcopy(resultado["estado"]), caixa=resultado["caixa"],
                divida=resultado["divida"], funcionarios=resultado["funcionarios"],
                marca=resultado["marca"], qualidade=resultado["qualidade"])
    return nova


class TestTradicional(unittest.TestCase):
    def assert_reconciliacao(self, resultado):
        dfc, balanco = resultado["detalhes"]["dfc"], resultado["detalhes"]["balanco"]
        self.assertAlmostEqual(dfc["caixa_inicial"] + dfc["variacao"], resultado["caixa"], places=2)
        self.assertAlmostEqual(dfc["operacional"] + dfc["investimento"] + dfc["financiamento"], dfc["variacao"], places=2)
        self.assertAlmostEqual(
            balanco["caixa"] + balanco["receber"] + balanco["estoques"] + balanco["imobilizado"]
            - balanco["pagar"] - balanco["divida"], balanco["patrimonio"], places=2,
        )

    def test_cadeia_completa_produz_vende_e_concilia(self):
        empresa, decisao, parametros = base()
        preparo = preparar(empresa, decisao, parametros, 1)
        resultado = apurar(preparo, 80, sem_tributos)
        self.assertEqual(preparo["producao_real"], 100)
        self.assertEqual(resultado["vendas"], 80)
        self.assertEqual(resultado["dre"]["receita"], 8_000.0)
        self.assertGreater(resultado["dre"]["cmv"], 0)
        self.assert_reconciliacao(resultado)

    def test_sem_mao_de_obra_sem_pro_labore_nao_ha_producao(self):
        empresa, decisao, parametros = base()
        empresa["funcionarios"] = 0
        preparo = preparar(empresa, decisao, parametros, 1)
        resultado = apurar(preparo, 80, sem_tributos)
        self.assertEqual(preparo["capacidade_produtiva"], 0)
        self.assertEqual(preparo["producao_real"], 0)
        self.assertEqual(resultado["vendas"], 0)

    def test_sem_marketing_ou_orcamento_de_frete_nao_ha_receita(self):
        empresa, decisao, parametros = base()
        sem_marketing = apurar(preparar(empresa, {**decisao, "marketing": 0.0}, parametros, 1), 80, sem_tributos)
        decisao_sem_frete = deepcopy(decisao)
        decisao_sem_frete["simulacao"]["orcamento_logistico"] = 0.0
        sem_frete = apurar(preparar(empresa, decisao_sem_frete, parametros, 1), 80, sem_tributos)
        self.assertEqual(sem_marketing["vendas"], 0)
        self.assertEqual(sem_frete["vendas"], 0)
        self.assertGreater(sem_frete["estado"]["estoque_pa"]["quantidade"], 0)

    def test_credito_reconhece_receita_agora_e_caixa_no_vencimento(self):
        empresa, decisao, parametros = base()
        decisao["simulacao"].update(vendas_prazo=1, prazo_recebimento=2)
        primeiro = apurar(preparar(empresa, decisao, parametros, 1), 50, sem_tributos)
        self.assertEqual(primeiro["dre"]["receita"], 5_000.0)
        self.assertTrue(primeiro["estado"]["receber"])
        empresa_2 = proxima_empresa(empresa, primeiro)
        decisao_2 = deepcopy(decisao)
        decisao_2["marketing"] = 0.0
        segundo = apurar(preparar(empresa_2, decisao_2, parametros, 2), 0, sem_tributos)
        empresa_3 = proxima_empresa(empresa_2, segundo)
        terceiro = apurar(preparar(empresa_3, decisao_2, parametros, 3), 0, sem_tributos)
        self.assertGreater(terceiro["detalhes"]["dfc"]["recebimentos"], 0)
        self.assertFalse(terceiro["estado"]["receber"])
        self.assert_reconciliacao(primeiro)
        self.assert_reconciliacao(segundo)
        self.assert_reconciliacao(terceiro)

    def test_refugo_consumiu_insumo_e_e_prejuizo_operacional(self):
        empresa, decisao, parametros = base()
        resultado = apurar(preparar(empresa, decisao, parametros, 1), 0, sem_tributos)
        self.assertEqual(resultado["detalhes"]["operacao"]["refugo"], 2)
        self.assertGreater(resultado["dre"]["refugos"], 0)
        self.assertEqual(resultado["estado"]["estoque_pa"]["quantidade"], 98)
        self.assert_reconciliacao(resultado)

    def test_maquina_comprada_nao_produz_na_semana_da_compra(self):
        empresa, decisao, parametros = base()
        empresa["estado_simulacao"]["maquinas"] = []
        decisao["simulacao"]["comprar_maquinas"] = 1
        primeiro = apurar(preparar(empresa, decisao, parametros, 1), 80, sem_tributos)
        self.assertEqual(primeiro["vendas"], 0)
        self.assertEqual(primeiro["estado"]["maquinas"][0]["ativacao"], 2)
        empresa_2 = proxima_empresa(empresa, primeiro)
        segundo = apurar(preparar(empresa_2, decisao, parametros, 2), 50, sem_tributos)
        self.assertGreater(segundo["vendas"], 0)
        self.assert_reconciliacao(primeiro)
        self.assert_reconciliacao(segundo)


if __name__ == "__main__":
    unittest.main()
