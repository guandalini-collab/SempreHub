"""Ciclos completos em turmas isoladas; nunca usam produção nem API paga."""
from copy import deepcopy
import pytest
from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar
from .test_avancado_api import _fechar
from .decisoes import completar_decisao


@pytest.mark.parametrize('modo', ['TRADICIONAL', 'STARTUP'])
def test_quatro_ciclos_autonomos(cliente, professor, modo):
    turma = _criar_turma(cliente, professor, modo_jogo=modo, total_rodadas=4,
                         configuracao_simulacao={'periodicidade':'SEMANAL','data_inicio_simulada':'2026-11-04'})
    aluno = cadastrar(cliente, 'QA Ciclo', f'ciclo-{modo}@aluno.iffar.edu.br')
    eid = _entrar(cliente, aluno, turma['codigo'], 'QA Ciclos', regime='SIMPLES_NACIONAL')
    historico = []
    for rodada in range(1, 5):
        simulacao=dict(
            comprar_maquinas=1 if rodada==3 and modo=='TRADICIONAL' else 0,
            comprar_mp=100 if rodada==1 else 0,
            producao=0 if rodada==3 else 20,
            manutencao=0 if rodada==3 else 1000,
            treinamento=0 if rodada==3 else 300,
            salario=2500, beneficio=0 if rodada==3 else 150,
            capacidade_nuvem=100,
            pro_labore=1_500 if rodada != 3 else 0,
            modal='ECONOMICO' if rodada==3 else 'RAPIDO')
        # O teste valida o ciclo contábil, não uma campanha. Marketing sem um
        # catálogo publicado precisa continuar zerado pela regra nova.
        envio=cliente.put(f'/api/aluno/empresas/{eid}/decisao',headers=aluno,json=completar_decisao(dict(rodada=rodada,preco=100,marketing=0,contratar=3 if rodada==1 else 2 if rodada==4 else 0,demitir=3 if rodada==3 else 0,simulacao=simulacao)))
        assert envio.status_code==200,envio.text
        _fechar(cliente, professor, turma, rodada)
        painel = cliente.get(f'/api/aluno/empresas/{eid}', headers=aluno).json()
        resultado = painel['resultados'][-1]
        assert painel['resultados'][:-1] == historico
        historico = deepcopy(painel['resultados'])
        detalhe = resultado['detalhes_simulacao']
        b, dre = detalhe['balanco'], detalhe['dre']
        assert b['ativo_total'] == pytest.approx(b['passivo_total']+b['patrimonio'], abs=.01)
        assert dre['receita']-sum(v for k,v in dre.items() if k not in ('receita','lucro_liquido')) == pytest.approx(dre['lucro_liquido'], abs=.01)
        dados = cliente.get(f'/api/aluno/empresas/{eid}/dashboard/{rodada}',headers=aluno)
        assert dados.status_code == 200, dados.text
        docente = cliente.get(f"/api/professor/turmas/{turma['id']}/empresas/{eid}/dashboard/{rodada}",headers=professor)
        assert docente.status_code == 200
        assert docente.json()['indicadores'] == dados.json()['indicadores']
        if rodada==3:
            assert resultado['funcionarios']==0
            assert dados.json()['indicadores']['rh']['eNPS']['estado']=='Não se aplica'
            assert dados.json()['indicadores']['producao']['OEE']['estado']=='Não se aplica'
        print(f"{modo}: rodada {rodada} encerrada; DRE e balanço conciliados; ambos os perfis conferem.")
    final=cliente.get(f"/api/professor/turmas/{turma['id']}",headers=professor).json()
    assert final['turma']['status']=='ENCERRADA'
