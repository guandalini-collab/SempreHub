"""Acesso HTTP comum: identificação, tempo limite e novas tentativas."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

AGENTE = "SempreHub-fontes/1.0 (uso academico; IFFar)"


def _abrir(req, tempo, tentativas):
    erro = None
    for n in range(tentativas):
        try:
            with urllib.request.urlopen(req, timeout=tempo) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as e:  # HTTPError herda de URLError
            erro = e
            if isinstance(e, urllib.error.HTTPError) and e.code < 500 and e.code != 429:
                break
            if "CERTIFICATE" in str(e):  # certificado ausente não se resolve tentando de novo
                break
            # 429 = limite de taxa (o GDELT pede intervalo de alguns segundos entre consultas).
            limite = isinstance(e, urllib.error.HTTPError) and e.code == 429
            time.sleep((6.0 if limite else 1.5) * (n + 1))
    raise RuntimeError(f"Falha ao consultar {req.full_url}: {erro}")


def url(base: str, params: dict | None = None) -> str:
    # Espaço vira %20 (não "+"): a API OData do BCB recusa "+" no $filter (erro 400 em 19/11/2026).
    return base + ("?" + urllib.parse.urlencode(params, safe="[]|,:'$", quote_via=urllib.parse.quote) if params else "")


def obter_texto(endereco: str, tempo: int = 30, tentativas: int = 3, cabecalhos: dict | None = None) -> str:
    req = urllib.request.Request(endereco, headers={"User-Agent": AGENTE, **(cabecalhos or {})})
    return _abrir(req, tempo, tentativas).decode("utf-8", errors="replace")


def obter_json(endereco: str, tempo: int = 30, tentativas: int = 3, cabecalhos: dict | None = None):
    return json.loads(obter_texto(endereco, tempo, tentativas, cabecalhos))


def enviar_json(endereco: str, corpo: dict, tempo: int = 60, tentativas: int = 3):
    req = urllib.request.Request(endereco, data=json.dumps(corpo).encode("utf-8"), method="POST",
                                 headers={"User-Agent": AGENTE, "Content-Type": "application/json"})
    return json.loads(_abrir(req, tempo, tentativas).decode("utf-8"))
