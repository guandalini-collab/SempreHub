"""Fontes primárias: lista institucional explícita, sem portais comerciais."""
from urllib.parse import urlsplit

DOMINIOS = ('gov.br', 'leg.br', 'ibge.gov.br', 'ipea.gov.br', 'bcb.gov.br',
            'fiocruz.br', 'fgv.br', 'usp.br', 'unicamp.br', 'ufrj.br')


def fonte_oficial(url):
    try:
        u=urlsplit(url)
        host=(u.hostname or '').lower().rstrip('.')
        return (u.scheme=='https' and not u.username and not u.password and u.port in (None,443)
                and any(host==d or host.endswith('.'+d) for d in DOMINIOS))
    except ValueError:
        return False
