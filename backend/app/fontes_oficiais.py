"""Fontes institucionais permitidas, sem portais comerciais ou agregadores."""
from urllib.parse import urlsplit

# A pesquisa do simulador só pode recorrer a fontes primárias governamentais,
# entidades setoriais e institutos de pesquisa reconhecidos. A lista explícita
# evita que a busca encontre blogs, varejistas ou páginas de opinião.
DOMINIOS_GERAIS = (
    'gov.br', 'leg.br', 'dados.gov.br',
    'ibge.gov.br', 'ipea.gov.br', 'ipeadata.gov.br', 'bcb.gov.br',
    'inmet.gov.br', 'inpi.gov.br', 'fiocruz.br', 'fgv.br', 'fipe.org.br',
    'cni.com.br', 'cnc.org.br', 'anbima.com.br', 'anfavea.com.br',
    'seade.gov.br', 'usp.br', 'unicamp.br', 'ufrj.br',
)

# Sebrae: serviço social autônomo; vale para todos os setores.
DOMINIOS_SEBRAE = ('sebrae.com.br', 'datasebrae.com.br', 'agenciasebrae.com.br')

# Entidades setoriais por setor do simulador. Só entram domínios conferidos em
# publicações hospedadas no próprio domínio (consulta de 14/11/2026). Entidades
# cujo domínio não foi confirmado ficam de fora até a conferência; consultorias
# pagas (Statista, Gartner, IDC, Euromonitor, Mintel, IEMI, Kantar) não entram,
# pois o sistema não consegue abrir a página para confirmar trecho e data.
DOMINIOS_SETORIAIS = {
    # Seis setores do catálogo fixo (16/11/2026). Abicol e Abimóvel ficam de
    # fora até a conferência de publicação hospedada no próprio domínio.
    'Colchões e Dormitório': (),
    'Móveis Residenciais': (),
    'Vestuário e Moda Básica': ('abit.org.br', 'abvtex.org.br'),
    'Bicicletas e Mobilidade Leve': ('abraciclo.com.br', 'aliancabike.org.br'),
    'Pet Shop': ('abinpet.org.br', 'abempet.org.br', 'sindan.org.br'),
    'Mochilas, Malas e Bolsas': ('abicalcados.com.br',),
}

# Organismos internacionais públicos e gratuitos, com dados por país.
DOMINIOS_INTERNACIONAIS_SETORIAIS: dict[str, tuple] = {}

_TODOS_SETORIAIS = tuple(dict.fromkeys(
    d for grupo in (*DOMINIOS_SETORIAIS.values(), *DOMINIOS_INTERNACIONAIS_SETORIAIS.values()) for d in grupo
))
DOMINIOS = tuple(dict.fromkeys(DOMINIOS_GERAIS + DOMINIOS_SEBRAE + _TODOS_SETORIAIS))

# Termos para a segunda tentativa de busca, quando a primeira não encontra
# evidência: classificações oficiais (CNAE 2.0 e capítulos da NCM) e
# pesquisas do IBGE que cobrem o setor.
TERMOS_AMPLIACAO = {
    'Colchões e Dormitório': 'CNAE 31.04-7 e 47.54-7/02; NCM 9404.21 e 9404.29; Inmetro colchões; PMC móveis',
    'Móveis Residenciais': 'CNAE divisão 31; grupos 47.54 e 47.59; NCM capítulo 94; PIA-Produto; PMC móveis',
    'Vestuário e Moda Básica': 'CNAE divisão 14; grupo 47.81; NCM capítulos 61 e 62; PIM-PF; PMC tecidos, vestuário e calçados',
    'Bicicletas e Mobilidade Leve': 'CNAE 30.92-0 e 47.63-6/03; NCM 8712; Resolução Contran 996/2023; PMC outros artigos',
    'Pet Shop': 'CNAE 10.66-0, 47.89-0/04 e 96.09-2/08; NCM 2309.10; PNS domicílios com cães e gatos',
    'Mochilas, Malas e Bolsas': 'CNAE 15.21-1 e 47.82-2/02; NCM 4202; PMC tecidos, vestuário e calçados',
}


def dominios_para(setor=None):
    """Domínios gerais, Sebrae e entidades do setor informado."""
    if setor not in DOMINIOS_SETORIAIS:
        return DOMINIOS_GERAIS + DOMINIOS_SEBRAE
    return tuple(dict.fromkeys(
        DOMINIOS_GERAIS + DOMINIOS_SEBRAE + DOMINIOS_SETORIAIS[setor]
        + DOMINIOS_INTERNACIONAIS_SETORIAIS.get(setor, ())
    ))


def _host(url):
    u = urlsplit(url)
    host = (u.hostname or '').lower().rstrip('.')
    if u.scheme != 'https' or u.username or u.password or u.port not in (None, 443):
        return None
    return host


def _pertence(host, dominios):
    return any(host == d or host.endswith('.' + d) for d in dominios)


def fonte_oficial(url, dominios=DOMINIOS):
    try:
        host = _host(url)
        return bool(host) and _pertence(host, dominios)
    except ValueError:
        return False


def natureza_fonte(url):
    """Classifica a fonte para exibição ao professor e aos alunos."""
    try:
        host = _host(url)
    except ValueError:
        return ''
    if not host:
        return ''
    if _pertence(host, DOMINIOS_GERAIS):
        return 'governamental ou instituto de pesquisa'
    if _pertence(host, tuple(d for g in DOMINIOS_INTERNACIONAIS_SETORIAIS.values() for d in g)):
        return 'organismo internacional'
    if _pertence(host, DOMINIOS_SEBRAE + _TODOS_SETORIAIS):
        return 'fonte não governamental'
    if _pertence(host, DOMINIOS_IMPRENSA):
        return 'imprensa'
    if not _pertence(host, DOMINIOS_BLOQUEADOS):
        return 'fonte de mercado (site não oficial)'
    return ''


# Camadas da pesquisa de mercado. A camada 1 (órgãos públicos, institutos,
# Sebrae e entidades do setor) é sempre a primeira. As demais só completam as
# notícias e análises que a anterior não conseguiu confirmar; em todas, o item
# precisa de página real, aberta pelo sistema, com data de publicação conferida.
CAMADAS = (1, 2, 3)

# Camada 2: imprensa de acesso aberto (sem muro de assinatura, para que a
# página possa ser aberta e conferida).
DOMINIOS_IMPRENSA = (
    'agenciabrasil.ebc.com.br', 'g1.globo.com', 'cnnbrasil.com.br', 'exame.com',
    'infomoney.com.br', 'mercadoeconsumo.com.br', 'ecommercebrasil.com.br',
)

# Camada 3: web aberta, exceto redes sociais, vídeos, fóruns, lojas,
# marketplaces e encurtadores, que não são fonte de informação de mercado.
DOMINIOS_BLOQUEADOS = (
    'facebook.com', 'instagram.com', 'x.com', 'twitter.com', 'tiktok.com', 'youtube.com', 'youtu.be',
    'linkedin.com', 'reddit.com', 'pinterest.com', 'threads.net', 'kwai.com', 'whatsapp.com', 't.me',
    'quora.com', 'medium.com', 'blogspot.com', 'wordpress.com',
    'mercadolivre.com.br', 'amazon.com.br', 'amazon.com', 'shopee.com.br', 'magazineluiza.com.br',
    'magalu.com.br', 'aliexpress.com', 'americanas.com.br', 'casasbahia.com.br', 'temu.com', 'shein.com',
    'olx.com.br', 'submarino.com.br', 'kabum.com.br',
    'bit.ly', 'tinyurl.com', 'encurtador.com.br', 'cutt.ly',
)


def fonte_da_camada(url, camada, setor=None):
    """Indica se o endereço pode ser citado na camada informada."""
    try:
        host = _host(url)
    except ValueError:
        return False
    if not host or _pertence(host, DOMINIOS_BLOQUEADOS):
        return False
    if camada == 1:
        return _pertence(host, dominios_para(setor))
    if camada == 2:
        return _pertence(host, DOMINIOS_IMPRENSA)
    return camada == 3


def fonte_permitida(url):
    """Fonte aceitável em alguma camada (usada na revisão e na publicação)."""
    return fonte_oficial(url) or fonte_da_camada(url, 2) or fonte_da_camada(url, 3)
