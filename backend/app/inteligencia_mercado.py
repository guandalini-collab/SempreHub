"""Pesquisa com fontes rastreáveis; credenciais nunca entram em respostas/logs."""
from copy import deepcopy
import json
import os
import urllib.error
import urllib.request
from fastapi import HTTPException


def _schema_estrito(schema):
    """A API garante a estrutura; limites de conteúdo continuam na validação local."""
    schema = deepcopy(schema)

    def preparar(node):
        if isinstance(node, dict):
            for chave in ("minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
                node.pop(chave, None)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for valor in node.values():
                preparar(valor)
        elif isinstance(node, list):
            for valor in node:
                preparar(valor)

    preparar(schema)
    return schema


def _solicitar(corpo, chave):
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses", data=json.dumps(corpo).encode(),
        headers={"Authorization": "Bearer " + chave, "Content-Type": "application/json"},
    )
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
    for item in saida.get("output", []):
        if item.get("type") == "web_search_call":
            fontes.update(s["url"] for s in item.get("action", {}).get("sources", []) if s.get("url"))
    return texto, fontes


def gerar_json(instrucoes, dados, pesquisar=False, schema=None, permitir_projecoes=False):
    chave = os.getenv("OPENAI_API_KEY") or os.getenv("SEMPREHUB_OPENAI_API_KEY")
    if not chave:
        raise HTTPException(503, "Integração de pesquisa indisponível. Configure a credencial no serviço.")
    corpo = {"model": os.getenv("SEMPREHUB_OPENAI_MODEL", "gpt-4.1-mini"), "store": False,
             "max_output_tokens": 10000,
             "input": [{"role": "system", "content": instrucoes + " Responda exclusivamente com JSON válido."},
                       {"role": "user", "content": json.dumps(dados, ensure_ascii=False)}]}
    if pesquisar:
        # A busca produz evidência citada. A formatação ocorre separadamente,
        # pois marcações de citação e blocos Markdown não compõem o JSON final.
        corpo["input"][0]["content"] = instrucoes + " Primeiro pesquise e apresente evidências com citações, preços de aquisição, datas e unidades. Não precisa produzir JSON nesta etapa. Se não encontrar algo, declare a falta de evidência; não invente."
        corpo["tools"] = [{"type": "web_search"}]
        corpo["include"] = ["web_search_call.action.sources"]
        corpo["tool_choice"] = "required"
    else:
        corpo["text"] = {"format": {"type": "json_schema", "name": "edicao_mercado", "strict": True, "schema": _schema_estrito(schema)} if schema else {"type": "json_object"}}
    texto, fontes = _solicitar(corpo, chave)
    if pesquisar:
        if not texto or not fontes:
            raise HTTPException(502, "A busca não encontrou evidências com fontes confirmadas. Nenhuma edição foi salva.")
        regra_projecao = " Quando solicitado, inclua projeções separadas dos fatos confirmados, identificadas como Projeção e acompanhadas das premissas usadas; nunca apresente essas estimativas como fatos." if permitir_projecoes else ""
        resultado, _ = gerar_json(
            instrucoes + regra_projecao + " Organize exclusivamente a evidência fornecida. Use somente URLs confirmadas. Não faça afirmações factuais adicionais nem invente custos, datas ou URLs. Quando autorizadas acima, projeções devem ser identificadas e acompanhadas das premissas, sem se passar por evidência. Cada id de produto deve ser uma string. Se faltarem evidências, retorne menos itens nos respectivos arrays; nunca complete quantidades com dados inventados.",
            {"solicitacao": dados, "evidencia": texto, "fontes_confirmadas": sorted(fontes)},
            False, schema, permitir_projecoes,
        )
        return resultado, fontes
    try:
        return json.loads(texto), fontes
    except (ValueError, TypeError):
        raise HTTPException(502, "A pesquisa retornou conteúdo inválido; nenhuma edição foi salva.") from None
