"""Pesquisa com fontes rastreáveis; credenciais nunca entram em respostas/logs."""
import json
import os
import urllib.error
import urllib.request
from fastapi import HTTPException


def gerar_json(instrucoes, dados, pesquisar=False):
    chave = os.getenv("OPENAI_API_KEY") or os.getenv("SEMPREHUB_OPENAI_API_KEY")
    if not chave:
        raise HTTPException(503, "Integração de pesquisa indisponível. Configure a credencial no serviço.")
    corpo = {"model": os.getenv("SEMPREHUB_OPENAI_MODEL", "gpt-4.1-mini"), "store": False,
             "max_output_tokens": 10000,
             "input": [{"role": "system", "content": instrucoes + " Responda exclusivamente com JSON válido."},
                       {"role": "user", "content": json.dumps(dados, ensure_ascii=False)}]}
    if pesquisar:
        corpo["tools"] = [{"type": "web_search_preview"}]
        corpo["tool_choice"] = "required"
    else:
        corpo["text"] = {"format": {"type": "json_object"}}
    req = urllib.request.Request("https://api.openai.com/v1/responses", data=json.dumps(corpo).encode(),
                                 headers={"Authorization": "Bearer " + chave, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resposta:
            saida = json.load(resposta)
    except urllib.error.HTTPError as e:
        raise HTTPException(502, f"A integração de pesquisa recusou a solicitação (HTTP {e.code}). Verifique credencial, saldo e acesso ao modelo.") from None
    except (urllib.error.URLError, TimeoutError):
        raise HTTPException(502, "A pesquisa não respondeu. Tente novamente.") from None
    if saida.get("status") == "incomplete":
        raise HTTPException(502, "A pesquisa excedeu o limite de resposta; reduza as quantidades e tente novamente.")
    texto = "".join(c.get("text", "") for o in saida.get("output", []) for c in o.get("content", []) if c.get("type") == "output_text")
    fontes = {a["url"] for o in saida.get("output", []) for c in o.get("content", []) for a in c.get("annotations", []) if a.get("type") == "url_citation" and a.get("url")}
    try:
        resultado = json.loads(texto)
    except (ValueError, TypeError):
        if pesquisar and texto and fontes:
            # Citações anexadas pela busca podem interromper o JSON. A segunda
            # chamada somente organiza a evidência; URLs continuam validadas.
            resultado, _ = gerar_json(
                instrucoes + " Organize exclusivamente a evidência fornecida. Não faça afirmações adicionais nem invente URLs ou valores.",
                {"solicitacao": dados, "evidencia": texto, "fontes_confirmadas": sorted(fontes)},
            )
            return resultado, fontes
        raise HTTPException(502, "A pesquisa retornou conteúdo inválido; nenhuma edição foi salva.") from None
    return resultado, fontes
