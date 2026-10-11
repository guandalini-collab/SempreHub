"""Confere preços e datas no documento citado, sem confiar na resposta do motor."""
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
import http.client
import ipaddress
import json
import re
import socket
import ssl
import unicodedata
from urllib.parse import urlsplit, urljoin

from fastapi import HTTPException


def normalizar(texto):
    texto = unicodedata.normalize("NFKC", texto).replace("\u200b", "")
    return " ".join(texto.split()).casefold()


class Documento(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.partes, self.datas, self.ignorar, self.jsonld = [], set(), 0, None
        self.feed(html)
        self.texto = normalizar(" ".join(self.partes))

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


def obter_documento(url):
    """HTTPS público, IP fixado na conexão, redirects conferidos e resposta limitada."""
    for _ in range(4):
        u = urlsplit(url)
        if u.scheme != "https" or not u.hostname or u.username or u.password or u.port not in (None, 443):
            raise ValueError("Fonte precisa usar HTTPS público.")
        ips = {r[4][0] for r in socket.getaddrinfo(u.hostname, 443, type=socket.SOCK_STREAM)}
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise ValueError("Fonte não pública.")
        # A conexão não resolve o hostname novamente, impedindo DNS rebinding.
        conexao = http.client.HTTPSConnection(u.hostname, timeout=10, context=ssl.create_default_context())
        conexao.sock = conexao._context.wrap_socket(
            socket.create_connection((sorted(ips)[0], 443), timeout=10), server_hostname=u.hostname,
        )
        try:
            conexao.request("GET", (u.path or "/") + ("?" + u.query if u.query else ""),
                            headers={"User-Agent": "SempreHub/validacao-fontes", "Accept-Encoding": "identity"})
            resposta = conexao.getresponse()
            if resposta.status in (301, 302, 303, 307, 308):
                url = urljoin(url, resposta.getheader("Location", ""))
                continue
            if resposta.status != 200 or "html" not in resposta.getheader("Content-Type", "").lower():
                raise ValueError("Documento não disponível como HTML.")
            corpo = resposta.read(2_000_001)
            if len(corpo) > 2_000_000 or resposta.getheader("Content-Encoding", "identity") != "identity":
                raise ValueError("Documento excede os limites de leitura.")
            return Documento(corpo.decode(resposta.headers.get_content_charset() or "utf-8", errors="replace"))
        finally:
            conexao.close()
    raise ValueError("Excesso de redirecionamentos.")


def validar_evidencias(edicao):
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
            except (OSError, ValueError, http.client.HTTPException):
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
