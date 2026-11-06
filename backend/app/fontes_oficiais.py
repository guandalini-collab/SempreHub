"""Fontes institucionais permitidas, sem portais comerciais ou agregadores."""
from urllib.parse import urlsplit

# A pesquisa do simulador só pode recorrer a fontes primárias governamentais,
# entidades setoriais e institutos de pesquisa reconhecidos. A lista explícita
# evita que a busca encontre blogs, varejistas ou páginas de opinião.
DOMINIOS = (
    'gov.br', 'leg.br', 'dados.gov.br',
    'ibge.gov.br', 'ipea.gov.br', 'ipeadata.gov.br', 'bcb.gov.br',
    'inmet.gov.br', 'inpi.gov.br', 'fiocruz.br', 'fgv.br', 'fipe.org.br',
    'cni.com.br', 'cnc.org.br', 'anbima.com.br', 'anfavea.com.br',
    'seade.gov.br', 'usp.br', 'unicamp.br', 'ufrj.br',
)


def fonte_oficial(url):
    try:
        u=urlsplit(url)
        host=(u.hostname or '').lower().rstrip('.')
        return (u.scheme=='https' and not u.username and not u.password and u.port in (None,443)
                and any(host==d or host.endswith('.'+d) for d in DOMINIOS))
    except ValueError:
        return False
