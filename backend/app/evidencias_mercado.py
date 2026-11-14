"""Confere preços e datas no documento citado, sem confiar na resposta do motor."""
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
import http.client
import ipaddress
import json
import logging
import re
import socket
import ssl
import unicodedata
from urllib.parse import urlsplit, urljoin

from fastapi import HTTPException

_log = logging.getLogger("uvicorn.error")


def normalizar(texto):
    texto = unicodedata.normalize("NFKC", texto).replace("\u200b", "")
    return " ".join(texto.split()).casefold()


class Documento(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.partes, self.datas, self.ignorar, self.jsonld = [], set(), 0, None
        self.feed(html)
        self.texto = normalizar(" ".join(self.partes))
        # Muitos portais públicos (ex.: Agência de Notícias do IBGE) mostram a
        # data só no cabeçalho visível, sem metadado. Aceita-se a data
        # dd/mm/aaaa que aparece no início do texto da página.
        for achado in re.finditer(r"\b(\d{2})/(\d{2})/(\d{4})\b", self.texto[:3000]):
            if re.search(r"atualizad[oa]\s*(em)?\s*:?\s*$", self.texto[max(0, achado.start() - 20):achado.start()]):
                continue  # data de atualização não é data de publicação
            dia, mes, ano = achado.groups()
            self.datas.add(f"{ano}-{mes}-{dia}")

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("property", a.get("name", "")).lower() in (
            "article:published_time", "datepublished", "date", "pubdate", "datecreated",
        ):
            self.datas.add(a.get("content", "")[:10])
        if tag in ("script", "style", "nav", "footer"):
            self.ignorar += 1
            if tag == "script" and a.get("type") == "application/ld+json":
                self.jsonld = []

    def handle_endtag(self, tag):
        if tag == "script" and self.jsonld is not None:
            try:
                self._datas_json(json.loads("".join(self.jsonld)))
            except (ValueError, TypeError):
                pass
            self.jsonld = None
        if tag in ("script", "style", "nav", "footer"):
            self.ignorar = max(0, self.ignorar - 1)

    def _datas_json(self, valor):
        if isinstance(valor, dict):
            if isinstance(valor.get("datePublished"), str):
                self.datas.add(valor["datePublished"][:10])
            for v in valor.values():
                self._datas_json(v)
        elif isinstance(valor, list):
            for v in valor:
                self._datas_json(v)

    def handle_data(self, texto):
        if self.jsonld is not None:
            self.jsonld.append(texto)
        if not self.ignorar:
            self.partes.append(texto)


class FonteInsegura(ValueError):
    pass


def obter_documento(url, somente_oficial=True):
    """HTTPS público, IP fixado na conexão, redirects conferidos e resposta limitada."""
    for _ in range(4):
        if somente_oficial:
            from .fontes_oficiais import fonte_oficial
            if not fonte_oficial(url):
                raise FonteInsegura('Fonte ou redirecionamento não oficial.')
        u = urlsplit(url)
        if u.scheme != "https" or not u.hostname or u.username or u.password or u.port not in (None, 443):
            raise FonteInsegura("Fonte precisa usar HTTPS público.")
        ips = {r[4][0] for r in socket.getaddrinfo(u.hostname, 443, type=socket.SOCK_STREAM)}
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise FonteInsegura("Fonte não pública.")
        # A conexão não resolve o hostname novamente, impedindo DNS rebinding.
        conexao = http.client.HTTPSConnection(u.hostname, timeout=10, context=ssl.create_default_context())
        conexao.sock = conexao._context.wrap_socket(
            socket.create_connection((sorted(ips)[0], 443), timeout=10), server_hostname=u.hostname,
        )
        try:
            conexao.request("GET", (u.path or "/") + ("?" + u.query if u.query else ""),
                            headers={"User-Agent": "Mozilla/5.0 (compatible; SempreHub/1.0; +https://www.semprehub.com.br)",
                                     "Accept": "text/html,application/xhtml+xml", "Accept-Language": "pt-BR,pt;q=0.9",
                                     "Accept-Encoding": "identity"})
            resposta = conexao.getresponse()
            if resposta.status in (301, 302, 303, 307, 308):
                url = urljoin(url, resposta.getheader("Location", ""))
                continue
            if resposta.status != 200 or "html" not in resposta.getheader("Content-Type", "").lower():
                raise ValueError(f"Documento não disponível como HTML (HTTP {resposta.status}, "
                                 f"{resposta.getheader('Content-Type', '')[:60]}).")
            corpo = resposta.read(2_000_001)
            if len(corpo) > 2_000_000 or resposta.getheader("Content-Encoding", "identity") != "identity":
                raise ValueError("Documento excede os limites de leitura.")
            return Documento(corpo.decode(resposta.headers.get_content_charset() or "utf-8", errors="replace"))
        finally:
            conexao.close()
    raise ValueError("Excesso de redirecionamentos.")


def _validar_estritamente(edicao):
    documentos = {}
    # Falta de prova deve ser informada antes de qualquer consulta externa.
    for produto in edicao.produtos:
        prova = produto.evidencia_custo
        if not prova or prova.url not in {f.url for f in produto.fontes}:
            raise HTTPException(422, "O custo do produto precisa de um trecho literal e da URL da fonte que documenta esse preço. Nenhuma edição foi salva ou publicada.")

    def documento(url):
        if url not in documentos:
            try:
                documentos[url] = obter_documento(url)
            except FonteInsegura:
                raise
            except (OSError, ValueError, http.client.HTTPException) as erro:
                _log.warning("pesquisa: leitura falhou em %s: %s: %s", url, type(erro).__name__, str(erro)[:200])
                raise HTTPException(422, "Não foi possível conferir o conteúdo de uma fonte. A edição não pode ser salva ou publicada; use uma fonte acessível.") from None
        return documentos[url]

    def data_confere(item, permitir_consulta=False):
        data = item.data.strip()
        if permitir_consulta and data == "Consulta em " + datetime.now(timezone.utc).date().isoformat():
            return
        if not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", data):
            raise HTTPException(422, "Informe a data de publicação documentada (AAAA-MM ou AAAA-MM-DD). Para preço sem data publicada, use 'Consulta em AAAA-MM-DD' com a data de hoje.")
        for fonte in item.fontes:
            doc = documento(fonte.url)
            if any(d.startswith(data) for d in doc.datas if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)):
                return
        _log.warning("pesquisa: data %r não confere; datas lidas nas páginas %s: %s", data,
                     [f.url for f in item.fontes], sorted({d for f in item.fontes for d in documento(f.url).datas})[:10])
        raise HTTPException(422, "A data informada não corresponde à data de publicação das fontes. Nenhuma edição foi salva ou publicada.")

    for item in edicao.noticias + edicao.analises:
        data_confere(item)
    for produto in edicao.produtos:
        prova = produto.evidencia_custo
        trecho = normalizar(prova.trecho)
        if trecho not in documento(prova.url).texto or normalizar(produto.nome) not in trecho:
            raise HTTPException(422, "O trecho de custo não foi encontrado na fonte ou não identifica o mesmo produto. Use o nome documentado e copie o trecho literal do preço.")
        precos = re.findall(r"r\$\s*((?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{2})?)(?![\d,.])", trecho)
        valores = {Decimal(p.replace(".", "").replace(",", ".")) for p in precos}
        if valores != {Decimal(str(produto.custo_unitario))}:
            raise HTTPException(422, "O custo informado não corresponde ao preço em reais no trecho citado. Não é permitido preencher custos estimados como preços documentados.")
        data_confere(produto, permitir_consulta=True)


def _alerta_estimativa(motivo: str) -> str:
    """Alerta ao professor quando o custo cai no padrão da turma.

    As mensagens de validação estrita dizem que a edição não foi salva,
    o que é verdade só no modo estrito; aqui a edição segue com custo
    estimado, então a frase de bloqueio é retirada do motivo.
    """
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+", motivo) if f.strip()]
    causa = " ".join(f for f in frases if not re.search(r"nenhuma edição|não pode ser salva|não foi salva", f, re.I))
    return ("Custo documental não comprovado; aplicado o custo padrão da turma (Estimativa do Modelo). "
            + (f"Motivo: {causa}" if causa else "")).strip()


def _descartar_artigos_sem_prova(edicao):
    """Na pesquisa nova, retira só a notícia ou análise que não pôde ser conferida.

    Cada item continua passando pela conferência estrita (página acessível e
    data de publicação). O item reprovado não é corrigido nem completado: sai
    da edição, e o professor recebe o aviso antes de revisar e publicar.
    """
    descartados = []
    for campo, rotulo in (("noticias", "notícia"), ("analises", "análise")):
        mantidos = []
        for item in getattr(edicao, campo):
            vazio = {"noticias": [], "analises": [], "produtos": []}
            try:
                _validar_estritamente(edicao.model_copy(update={**vazio, campo: [item]}))
            except FonteInsegura:
                raise HTTPException(422, "Fonte bloqueada: use somente HTTPS público, sem endereços internos.") from None
            except HTTPException as erro:
                motivo = "data de publicação não confere com a página" if "data" in str(erro.detail).lower() else "página não pôde ser lida"
                descartados.append(f"{rotulo} “{item.titulo[:80]}” ({motivo}; {item.fontes[0].url[:120]})")
            else:
                mantidos.append(item)
        setattr(edicao, campo, mantidos)
    if descartados:
        aviso = ("Itens retirados porque a página citada não pôde ser conferida (página inacessível, arquivo PDF "
                 "ou data de publicação não identificada): " + "; ".join(descartados) + ". Nada foi completado sem fonte.")
        edicao.avisos = (list(edicao.avisos or []) + [aviso])[:10]


def validar_evidencias(edicao, turma=None, descartar_artigos=False):
    """Notícias estritas; custos projetados somente com base numérica explícita."""
    if turma is None:
        return _validar_estritamente(edicao)
    def custo_padrao():
        if turma.custo_unitario <= 0:
            raise HTTPException(422, "Configure um custo unitário padrão maior que zero na turma para permitir produtos estimados.")
        return turma.custo_unitario

    edicao.versao_custos_catalogo = "1.0.0-three-paths"
    if descartar_artigos:
        _descartar_artigos_sem_prova(edicao)
    artigos = edicao.model_copy(update={"produtos": []})
    try:
        _validar_estritamente(artigos)
    except FonteInsegura:
        raise HTTPException(422, "Fonte bloqueada: use somente HTTPS público, sem endereços internos.") from None
    for produto in edicao.produtos:
        try:
            # Valida o preço original, evitando aplicar 0,60 novamente na publicação.
            if produto.tipo_documento == "preco_varejo" and produto.valor_documentado is not None:
                produto.custo_unitario = produto.valor_documentado
            _validar_estritamente(edicao.model_copy(update={"noticias": [], "analises": [], "produtos": [produto]}))
        except FonteInsegura:
            raise HTTPException(422, "Fonte bloqueada: use somente HTTPS público, sem endereços internos.") from None
        except HTTPException as erro:
            produto.custo_unitario = custo_padrao()
            produto.valor_documentado = None
            produto.estado_indicador = "Estimativa do Modelo"
            produto.formula_aplicada = "Custo Padrão da Turma (Fallback por falha de leitura)"
            produto.alerta_professor = _alerta_estimativa(str(erro.detail))
            produto.base_custo = f"Estimativa do Modelo: custo padrão da turma de R$ {turma.custo_unitario:.2f}. Fonte não comprovada; não representa custo real documentado."
            produto.data = "Consulta em " + datetime.now(timezone.utc).date().isoformat()
        else:
            valor = produto.custo_unitario
            produto.valor_documentado = valor
            produto.alerta_professor = None
            if produto.tipo_documento == "preco_varejo":
                produto.custo_unitario = float((Decimal(str(valor)) * Decimal("0.60")).quantize(Decimal("0.01")))
                produto.estado_indicador = "Estimativa do Modelo"
                produto.formula_aplicada = "Preço de Varejo * 0.60"
                produto.base_custo = f"Estimativa do Modelo: preço de varejo documentado R$ {valor:.2f} × 0,60 (desconto didático de 40%). Não representa custo real de fabricação."
            else:
                produto.estado_indicador = "Valor Calculado"
                produto.formula_aplicada = "Preço documentado de aquisição"
            if produto.custo_unitario <= 0:
                produto.custo_unitario = custo_padrao()
                produto.estado_indicador = "Estimativa do Modelo"
                produto.formula_aplicada = "Custo Padrão da Turma"
                produto.alerta_professor = "Preço projetado abaixo de um centavo; aplicado custo padrão da turma."
