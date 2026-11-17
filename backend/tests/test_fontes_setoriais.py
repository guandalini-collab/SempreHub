"""Fontes setoriais por setor e segunda tentativa de busca com termos ampliados."""
import pytest
from fastapi import HTTPException
from app import inteligencia_mercado as ia
from app.fontes_oficiais import (DOMINIOS_SETORIAIS, TERMOS_AMPLIACAO, dominios_para,
                                 fonte_oficial, natureza_fonte)
from app.routers.mercado import SETORES, Fonte


def test_todo_setor_do_simulador_tem_mapa_e_termos():
    assert set(DOMINIOS_SETORIAIS) == set(SETORES) == set(TERMOS_AMPLIACAO)


def test_busca_restrita_ao_setor():
    pet = dominios_para('Pet Shop')
    assert 'abinpet.org.br' in pet and 'gov.br' in pet and 'datasebrae.com.br' in pet
    assert 'abraciclo.com.br' not in pet
    assert len(pet) <= 100  # limite de domínios do filtro da ferramenta
    assert 'abraciclo.com.br' not in dominios_para(None)


@pytest.mark.parametrize('url,natureza', [
    ('https://www.ibge.gov.br/x', 'governamental ou instituto de pesquisa'),
    ('https://www.abinpet.org.br/x', 'fonte não governamental'),
    ('https://datasebrae.com.br/x', 'fonte não governamental'),
    # Domínio que imita uma entidade não recebe a marcação da entidade.
    ('https://abinpet.org.br.evil.com/x', 'fonte de mercado (site não oficial)'),
    ('https://g1.globo.com/economia/x', 'imprensa'),
    ('https://www.instagram.com/p/x', ''),
])
def test_natureza_da_fonte(url, natureza):
    assert natureza_fonte(url) == natureza
    assert Fonte(titulo='t', url=url).natureza == natureza


def test_fonte_setorial_aceita_na_revisao_mas_falsificacao_nao():
    assert fonte_oficial('https://www.abit.org.br/panorama')
    assert not fonte_oficial('https://abit.org.br@evil.com/')


def test_segunda_tentativa_amplia_termos(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'somente-teste')
    vistos = []

    def solicitar(corpo, chave):
        vistos.append(corpo)
        if len(vistos) == 1:
            return '', set()
        if len(vistos) == 2:
            return 'Evidência ampliada', {'https://www.abinpet.org.br/numeros'}
        return '{"ok": true}', set()
    monkeypatch.setattr(ia, '_solicitar', solicitar)
    resultado, fontes = ia.gerar_json('Pesquise', {}, True, None, False, 'Pet Shop')
    assert resultado == {'ok': True} and fontes == {'https://www.abinpet.org.br/numeros'}
    assert 'abinpet.org.br' in vistos[0]['tools'][0]['filters']['allowed_domains']
    assert 'Amplie os termos' not in vistos[0]['input'][0]['content']
    assert 'NCM 2309.10' in vistos[1]['input'][0]['content']


def test_sem_evidencia_apos_ampliar_nao_salva(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'somente-teste')
    chamadas = []
    monkeypatch.setattr(ia, '_solicitar', lambda corpo, chave: chamadas.append(1) or ('', set()))
    with pytest.raises(HTTPException) as erro:
        ia.gerar_json('Pesquise', {}, True, None, False, 'Pet Shop')
    assert erro.value.status_code == 502 and len(chamadas) == 2


def test_fonte_de_outro_setor_e_recusada(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'somente-teste')
    monkeypatch.setattr(ia, '_solicitar', lambda corpo, chave: ('Texto', {'https://www.abraciclo.com.br/x'}))
    with pytest.raises(HTTPException):
        ia.gerar_json('Pesquise', {}, True, None, False, 'Pet Shop')
