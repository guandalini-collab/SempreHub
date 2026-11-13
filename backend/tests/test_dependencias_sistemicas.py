"""Testes isolados das dependências que sustentam o motor semanal.

Não dependem de FastAPI nem do banco. Podem ser executados com ``unittest``
para verificar as equações mesmo fora do ambiente de produção.
"""

import math
import unittest

from app.motor.dependencias import (
    atualizar_marca,
    atualizar_pd,
    atualizar_pd_por_produto,
    atrativo_porter,
    custo_unitario_com_barganha,
    radar_coerencia,
)
from app.catalogo_setorial import SETORES, enriquecer_produto
from app.motor.portfolio import atrativos, diagnostico_midia, diagnostico_segmentacao, limitar_por_capacidade, produzir
from app.motor.indicadores import capacidades_producao
from app.motor.tradicional import apurar, preparar
from app.motor import startup


class DependenciasSistemicasTest(unittest.TestCase):
    def test_linha_complexa_consome_mais_capacidade_por_unidade(self):
        resultado = limitar_por_capacidade([50, 50], [1.0, 1.2], 100)
        self.assertLess(sum(resultado), 100)
        self.assertLess(resultado[1], resultado[0])
        self.assertLessEqual(resultado[0] + resultado[1] * 1.2, 100)

    def test_insumo_de_uma_linha_nao_abastece_outra(self):
        estado = {
            "estoque_mp": {"quantidade": 0, "valor": 0},
            "estoque_pa": {"quantidade": 0, "valor": 0},
        }
        itens = [
            {"produto_id": "popular", "peso": 1, "custo_unitario": 10, "insumo_chave": "insumo_a"},
            {"produto_id": "premium", "peso": 1, "custo_unitario": 20, "insumo_chave": "insumo_b"},
        ]
        produzir(estado, itens, {
            "comprar_mp": 100,
            "comprar_insumos_por_produto": {"popular": 100, "premium": 0},
            "producao": 100,
        }, capacidade=100, maquinas=100, multiplicador=1)
        linhas = {linha["produto_id"]: linha for linha in estado["portfolio_producao"]}
        self.assertEqual(linhas["premium"]["producao_realizada"], 0)
        self.assertEqual(linhas["popular"]["insumo_comprado"], 100)
        self.assertEqual(linhas["premium"]["insumo_chave"], "insumo_b")

    def test_linha_especializada_sem_qualificacao_so_aproveita_20_porcento(self):
        estado = {"estoque_mp": {"quantidade": 0, "valor": 0}, "estoque_pa": {"quantidade": 0, "valor": 0}}
        itens = [{"produto_id": "inducao", "peso": 1, "custo_unitario": 10, "insumo_chave": "placa",
                  "linha_produto": "PREMIUM", "qualificacao_minima": "especialista"}]
        produzir(estado, itens, {"comprar_mp": 100, "comprar_insumos_por_produto": {"inducao": 100}, "producao": 100},
                 capacidade=100, maquinas=100, multiplicador=1,
                 taxas_defeito_linha={"inducao": .80},
                 qualificacao_linha={"inducao": {"compativel": False, "motivo": "Sem especialista"}})
        linha = estado["portfolio_producao"][0]
        self.assertEqual(linha["taxa_refugo"], .80)
        self.assertFalse(linha["qualificacao_compativel"])
        self.assertEqual(estado["estoques_produtos"]["inducao"]["estoque_pa"]["quantidade"], 20)

    def empresa_fisica(self):
        return {
            "caixa": 100_000.0,
            "divida": 0.0,
            "funcionarios": 1,
            "autoeficacia": 60,
            "regime_tributario": "SIMPLES_NACIONAL",
            "classe_dornelas": "SERIAL",
            "marca": 0.0,
            "qualidade": 0.0,
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

    def parametros_fisicos(self):
        return {
            "custo_unitario": 40.0, "produtividade_por_pessoa": 120.0,
            "custos_fixos_mensais": 0.0, "salario_base": 2_000.0,
            "taxa_juros_mensal": 0.0, "taxa_cheque_especial": 0.08,
            "limite_credito": 50_000.0, "preco_referencia": 100.0,
            "configuracao_simulacao": {
                "custo_armazenagem": 0.0, "frete_padrao": 5.0,
                "frete_rapido": 8.0, "frete_economico": 3.0,
                "preco_maquina": 12_000.0, "capacidade_maquina": 400, "vida_util": 24,
            },
        }

    def decisao_fisica(self, *, marketing=500.0, orcamento_logistico=500.0):
        produto = {
            "produto_id": "p1", "produto_nome": "Produto de teste", "peso": 1,
            "custo_unitario": 40.0, "preco": 100.0, "canais": ["DIRETO"],
            "posicionamento": "PRECO", "midias": [],
        }
        return {
            "preco": 100.0,
            "marketing": marketing,
            "pd": 0.0,
            "plano_comercial": {"produtos": [produto], "custo_unitario": 40.0},
            "simulacao": {
                "producao": 100, "comprar_mp": 100, "modal": "PADRAO",
                "orcamento_logistico": orcamento_logistico, "pro_labore": 0.0,
            },
        }

    @staticmethod
    def sem_tributos(receita, cmv):
        return 0.0, 0.0

    def test_marca_tem_retorno_decrescente_e_decaimento_sem_marketing(self):
        marca_1000 = atualizar_marca(0, 1000)
        marca_2000 = atualizar_marca(0, 2000)
        self.assertGreater(marca_2000, marca_1000)
        self.assertLess(marca_2000 - marca_1000, marca_1000)
        self.assertAlmostEqual(atualizar_marca(marca_1000, 0), marca_1000 * 0.85)

    def test_pd_respeita_fila_do_modelo(self):
        estado_startup = {}
        qualidade_1, prontos_1 = atualizar_pd(estado_startup, 0, 1000, 1, "STARTUP")
        self.assertEqual(prontos_1, [])
        qualidade_2, prontos_2 = atualizar_pd(estado_startup, qualidade_1, 0, 2, "STARTUP")
        self.assertEqual(len(prontos_2), 1)
        self.assertAlmostEqual(qualidade_2, math.log1p(1), places=7)

        estado_tradicional = {}
        qualidade_1, _ = atualizar_pd(estado_tradicional, 0, 1000, 1, "TRADICIONAL")
        qualidade_2, prontos_2 = atualizar_pd(estado_tradicional, qualidade_1, 0, 2, "TRADICIONAL")
        self.assertEqual(prontos_2, [])
        qualidade_3, prontos_3 = atualizar_pd(estado_tradicional, qualidade_2, 0, 3, "TRADICIONAL")
        self.assertEqual(len(prontos_3), 1)
        self.assertAlmostEqual(qualidade_3, math.log1p(1), places=7)

    def test_pd_por_produto_matura_apenas_na_linha_e_no_prazo_fisico(self):
        estado = {}
        itens = [
            {"produto_id": "popular", "peso": 1},
            {"produto_id": "premium", "peso": 3},
        ]
        primeira = atualizar_pd_por_produto(estado, itens, 4_000, 1, "TRADICIONAL")
        segunda = atualizar_pd_por_produto(estado, itens, 0, 2, "TRADICIONAL")
        terceira = atualizar_pd_por_produto(estado, itens, 0, 3, "TRADICIONAL")
        self.assertEqual(primeira["premium"]["nivel"], 0)
        self.assertEqual(segunda["premium"]["nivel"], 0)
        self.assertGreater(terceira["premium"]["nivel"], terceira["popular"]["nivel"])
        self.assertGreater(terceira["premium"]["reducao_custo"], 0)

    def test_capacidade_exige_trabalho_explicito_do_fundador_ou_equipe(self):
        sem_equipe = capacidades_producao(500, 0, 120, 1, 0, 1, 1, 40, fundador_ativo=False)
        com_fundador = capacidades_producao(500, 0, 120, 1, 0, 1, 1, 40, fundador_ativo=True)
        self.assertEqual(sem_equipe["capacidade_produtiva"], 0)
        self.assertGreater(com_fundador["capacidade_produtiva"], 0)

    def test_contratacao_tem_custo_integral_e_capacidade_parcial_na_integracao(self):
        decisao = self.decisao_fisica()
        decisao["contratar"] = 1
        preparo = preparar(self.empresa_fisica(), decisao, self.parametros_fisicos(), 1)
        integracao = preparo["kpis"]["integracao_equipe"]
        self.assertEqual(integracao["novatos"], 1)
        self.assertLess(integracao["fator"], 1.0)
        self.assertGreater(preparo["folha"], 0)
        self.assertTrue(any("integração" in alerta for alerta in preparo["alertas"]))

    def test_barganha_tem_teto_fisico(self):
        custo, desconto = custo_unitario_com_barganha(100, 1_000_000)
        self.assertEqual(desconto, 0.15)
        self.assertEqual(custo, 85.0)

    def test_radar_impede_demanda_sem_entrega_fisica(self):
        radar = radar_coerencia(
            modo="TRADICIONAL",
            decisao={"marketing": 500, "pd": 0, "simulacao": {"producao": 10, "comprar_mp": 10, "orcamento_logistico": 0, "pro_labore": 500}},
            plano_comercial={"produtos": [{"produto_id": "p1"}]},
            caixa=5_000,
            funcionarios=0,
            capacidade_operacional=10,
            estoque_disponivel=0,
            custo_frete_unitario=5,
        )
        self.assertFalse(radar["liberado"])
        self.assertTrue(any("logística" in texto for texto in radar["bloqueios"]))

    def test_radar_antecipa_deficit_de_caixa_sem_bloquear_a_decisao(self):
        radar = radar_coerencia(
            modo="TRADICIONAL",
            decisao={"marketing": 0, "pd": 0, "simulacao": {}},
            plano_comercial=None,
            caixa=1_000,
            funcionarios=0,
            capacidade_operacional=0,
            gastos_previstos=1_250,
        )
        self.assertTrue(radar["liberado"])
        self.assertTrue(any("Risco de caixa" in texto for texto in radar["avisos"]))

    def test_atratividade_nao_subtrai_reais_dos_indices(self):
        barata = atrativo_porter(2, 2, 80, 100)
        cara = atrativo_porter(2, 2, 120, 100)
        self.assertGreater(barata, cara)
        self.assertGreater(barata, 0)

    def test_catalogo_setorial_tem_quatro_linhas_por_setor(self):
        self.assertEqual(len(SETORES), 12)
        self.assertTrue(all(len(dados["categorias"]) == 4 for dados in SETORES.values()))
        notebook = enriquecer_produto("Eletrônicos e Tecnologia", {"id": "notebook"})
        self.assertEqual(notebook["linha_produto"], "PREMIUM")
        self.assertEqual(notebook["qualificacao_minima"], "especialista")
        self.assertIn("google", notebook["midias_recomendadas"])

    def test_midia_incompativel_e_cobrada_mas_nao_gera_atracao(self):
        produto = enriquecer_produto("Eletrônicos e Tecnologia", {"id": "notebook"})
        produto.update({"peso": 1, "custo_unitario": 40.0, "preco": 100.0,
                        "canais": ["DIRETO"], "posicionamento": "QUALIDADE"})
        produto["midias"] = [{"id": "carro-som", "quantidade": 2}]
        diagnostico = diagnostico_midia(produto)
        self.assertGreater(diagnostico["investimento_veiculacao"], 0)
        self.assertEqual(diagnostico["investimento_compativel"], 0)
        self.assertEqual(diagnostico["aderencia"], 0)
        produto["midias"] = [{"id": "google", "quantidade": 2}]
        self.assertEqual(diagnostico_midia(produto)["aderencia"], 1)
        produto["midias"] = [{"id": "carro-som", "quantidade": 2}]
        self.assertEqual(atrativos([produto], 100, 40), [0.0])

    def test_segmentacao_altera_a_demanda_por_preco_e_canais(self):
        produto = {
            "produto_id": "p1", "peso": 1, "custo_unitario": 40.0, "preco": 120.0,
            "canais": ["ECOMMERCE"], "cobertura": "NACIONAL", "posicionamento": "PRECO",
        }
        publico_compativel = {"preco_maximo": 150.0, "canais": ["ECOMMERCE"], "cobertura": "NACIONAL"}
        publico_incompativel = {"preco_maximo": 100.0, "canais": ["VAREJO"], "cobertura": "LOCAL"}
        self.assertGreater(atrativos([produto], 100, 40, segmentacao=publico_compativel)[0], 0)
        diagnostico = diagnostico_segmentacao(produto, publico_incompativel)
        self.assertEqual(diagnostico["fator"], 0.0)
        self.assertEqual(diagnostico["status"], "preco_acima_do_teto")

    def test_cadeia_fisica_completa_vende_apenas_com_comercial_e_entrega(self):
        preparo = preparar(
            self.empresa_fisica(), self.decisao_fisica(), self.parametros_fisicos(), 1,
        )
        resultado = apurar(preparo, 80, self.sem_tributos)
        self.assertGreater(preparo["producao_real"], 0)
        self.assertEqual(resultado["vendas"], 80)
        self.assertGreater(resultado["dre"]["receita"], 0)

    def test_marketing_ou_logistica_ausentes_zeram_a_venda_fisica(self):
        empresa = self.empresa_fisica()
        parametros = self.parametros_fisicos()
        sem_marketing = apurar(
            preparar(empresa, self.decisao_fisica(marketing=0), parametros, 1), 80, self.sem_tributos,
        )
        sem_logistica = apurar(
            preparar(empresa, self.decisao_fisica(orcamento_logistico=0), parametros, 1), 80, self.sem_tributos,
        )
        self.assertEqual(sem_marketing["vendas"], 0)
        self.assertEqual(sem_logistica["vendas"], 0)
        self.assertGreater(sem_logistica["estado"]["estoque_pa"]["quantidade"], 0)

    def test_linha_exige_capex_e_perde_capacidade_na_semana_de_setup(self):
        empresa = self.empresa_fisica()
        parametros = self.parametros_fisicos()
        decisao = self.decisao_fisica()
        produto = decisao["plano_comercial"]["produtos"][0]
        produto.update({"capex_ativacao": 2_000.0, "fator_setup": 1.2, "volume_armazenagem_m3": 3.0})
        decisao["simulacao"]["comprar_insumos_por_produto"] = {"p1": 100}

        preparo = preparar(empresa, decisao, parametros, 1)

        self.assertEqual(preparo["investimento_linhas"], 2_000.0)
        self.assertEqual(preparo["investimento"], 2_000.0)
        self.assertEqual(preparo["linhas_ativadas_agora"], ["Produto de teste"])
        self.assertGreater(preparo["penalidade_setup"], 0)
        self.assertLess(preparo["capacidade_produtiva"], 120)
        self.assertEqual(preparo["estado"]["ativos_linhas"][0]["produto_id"], "p1")

    def test_armazenagem_por_volume_e_lancada_no_resultado(self):
        empresa = self.empresa_fisica()
        parametros = self.parametros_fisicos()
        parametros["configuracao_simulacao"].update({"custo_armazenagem": 0.0, "custo_armazenagem_m3": 2.0})
        decisao = self.decisao_fisica(marketing=0, orcamento_logistico=0)
        produto = decisao["plano_comercial"]["produtos"][0]
        produto.update({"volume_armazenagem_m3": 3.0})
        decisao["simulacao"]["comprar_insumos_por_produto"] = {"p1": 100}

        resultado = apurar(preparar(empresa, decisao, parametros, 1), 0, self.sem_tributos)

        ocupacao = resultado["detalhes"]["operacao"]["ocupacao_armazenagem_m3"]
        self.assertGreater(ocupacao, 0)
        self.assertEqual(resultado["dre"]["armazenagem"], ocupacao * 2)

    def test_startup_exige_produto_marketing_e_capacidade_de_atendimento(self):
        empresa = {
            "caixa": 50_000.0, "divida": 0.0, "funcionarios": 0,
            "marca": 0.0, "qualidade": 0.0, "classe_dornelas": "SERIAL",
            "estado_simulacao": None,
        }
        parametros = {
            "preco_referencia": 100.0, "salario_base": 2_000.0,
            "custos_fixos_mensais": 0.0, "taxa_juros_mensal": 0.0,
            "taxa_cheque_especial": 0.08, "limite_credito": 50_000.0,
            "configuracao_simulacao": {"capacidade_atendimento_por_pessoa": 100},
        }
        produto = {
            "produto_id": "saas", "produto_nome": "Serviço", "peso": 1,
            "preco": 100.0, "custo_unitario": 10.0, "canais": ["DIRETO"],
            "posicionamento": "PRECO", "midias": [],
        }
        decisao = {
            "preco": 100.0, "marketing": 500.0, "pd": 0.0, "networking": 0.0,
            "contratar": 0, "demitir": 0, "emprestimo": 0.0, "amortizacao": 0.0,
            "plano_comercial": {"produtos": [produto], "custo_unitario": 10.0},
            "simulacao": {"capacidade_nuvem": 300, "pro_labore": 1_500.0},
        }
        completo = startup.apurar(startup.preparar(empresa, decisao, parametros, 1), 50, self.sem_tributos)
        sem_marketing = startup.apurar(
            startup.preparar(empresa, {**decisao, "marketing": 0.0}, parametros, 1), 50, self.sem_tributos,
        )
        sem_produto = startup.apurar(
            startup.preparar(empresa, {**decisao, "plano_comercial": None}, parametros, 1), 50, self.sem_tributos,
        )
        self.assertGreater(completo["vendas"], 0)
        self.assertEqual(sem_marketing["vendas"], 0)
        self.assertEqual(sem_produto["vendas"], 0)


if __name__ == "__main__":
    unittest.main()
