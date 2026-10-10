import pytest
from tests.conftest import cadastrar


@pytest.mark.parametrize('prefixo',['/api/manuais/','/manuais/'])
def test_pdf_protegido_por_sessao_e_perfil(cliente,professor,prefixo):
    aluno=cadastrar(cliente,'Ana','manual@aluno.iffar.edu.br')
    for arquivo in ['manual-aluno','manual-professor','manual-midias']:
        url=f'{prefixo}{arquivo}.pdf'
        assert cliente.get(url).status_code==401
        assert cliente.get(url,headers={'Authorization':'Bearer invalido'}).status_code==401
        r=cliente.get(url,headers=professor)
        assert r.status_code==200 and r.content.startswith(b'%PDF')
        assert r.headers['cache-control']=='private, no-store'
        r=cliente.get(url,headers=aluno)
        assert r.status_code==(403 if arquivo=='manual-professor' else 200)
    assert cliente.get(prefixo+'inexistente.pdf',headers=professor).status_code==404
