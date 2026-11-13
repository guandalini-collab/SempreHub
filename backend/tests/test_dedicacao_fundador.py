"""Dedicação do fundador proporcional ao pró-labore (Dornelas, cap. 6; Slack, cap. 11)."""
import unittest

from app.motor.indicadores import capacidades_producao, dedicacao_fundador
from tests.test_dependencias_sistemicas import DependenciasSistemicasTest as Base
from app.motor.tradicional import apurar, preparar
from app.motor import startup


class DedicacaoFundadorTest(unittest.TestCase):
    def test_sem_retirada_nao_ha_jornada(self):
        self.assertEqual(dedicacao_fundador(0, 2000, 1), 0.0)
        self.assertEqual(dedicacao_fundador(500, 0, 1), 0.0)

    def test_jornada_proporcional_e_limitada_a_uma(self):
        self.assertAlmostEqual(dedicacao_fundador(1000, 2000, 1), 0.5)
        self.assertEqual(dedicacao_fundador(5000, 2000, 1), 1.0)

    def test_referencia_semanal_usa_fracao_do_periodo(self):
        semana = 7 / 30
        self.assertAlmostEqual(dedicacao_fundador(2000 * semana / 2, 2000, semana), 0.5)

    def test_capacidade_cresce_com_a_dedicacao(self):
        meia = capacidades_producao(500, 0, 120, 1, 0, 1, 1, 220, dedicacao_fundador=0.5)
        inteira = capacidades_producao(500, 0, 120, 1, 0, 1, 1, 220, dedicacao_fundador=1.0)
        self.assertAlmostEqual(meia["capacidade_produtiva"] * 2, inteira["capacidade_produtiva"])
        self.assertTrue(meia["fundador_operante"])

    def test_pro_labore_simbolico_nao_produz_na_empresa_fisica(self):
        base = Base()
        empresa = base.empresa_fisica()
        empresa["funcionarios"] = 0
        decisao = base.decisao_fisica()
        decisao["simulacao"]["pro_labore"] = 1
        preparo = preparar(empresa, decisao, base.parametros_fisicos(), 1)
        self.assertLess(preparo["dedicacao_fundador"], 0.01)
        self.assertEqual(apurar(preparo, 80, base.sem_tributos)["vendas"], 0)

    def test_pro_labore_parcial_gera_alerta_e_capacidade_parcial(self):
        base = Base()
        empresa = base.empresa_fisica()
        empresa["funcionarios"] = 0
        decisao = base.decisao_fisica()
        decisao["simulacao"]["pro_labore"] = 1000
        preparo = preparar(empresa, decisao, base.parametros_fisicos(), 1)
        self.assertAlmostEqual(preparo["dedicacao_fundador"], 0.5)
        self.assertTrue(any("dedica 50%" in a for a in preparo["alertas"]))

    def test_startup_pro_labore_simbolico_nao_atende(self):
        empresa = {"caixa": 50_000.0, "divida": 0.0, "funcionarios": 0, "marca": 0.0, "qualidade": 0.0,
                   "classe_dornelas": "SERIAL", "estado_simulacao": None}
        parametros = {"preco_referencia": 100.0, "salario_base": 2_000.0, "custos_fixos_mensais": 0.0,
                      "taxa_juros_mensal": 0.0, "taxa_cheque_especial": 0.08, "limite_credito": 50_000.0,
                      "configuracao_simulacao": {"capacidade_atendimento_por_pessoa": 100}}
        produto = {"produto_id": "saas", "produto_nome": "Serviço", "peso": 1, "preco": 100.0,
                   "custo_unitario": 10.0, "canais": ["DIRETO"], "posicionamento": "PRECO", "midias": []}
        decisao = {"preco": 100.0, "marketing": 500.0, "pd": 0.0, "networking": 0.0, "contratar": 0,
                   "demitir": 0, "emprestimo": 0.0, "amortizacao": 0.0,
                   "plano_comercial": {"produtos": [produto], "custo_unitario": 10.0},
                   "simulacao": {"capacidade_nuvem": 300, "pro_labore": 1.0}}
        resultado = startup.apurar(startup.preparar(empresa, decisao, parametros, 1), 50, lambda r, c: (0.0, 0.0))
        self.assertEqual(resultado["vendas"], 0)


if __name__ == "__main__":
    unittest.main()
