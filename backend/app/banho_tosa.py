"""Banho e tosa no setor pet (turmas com catálogo), aprovado em 23/11/2026.

Regras e fontes:
- Capacidade por medida de entrada (Krajewski; Ritzman; Malhotra, 2009,
  p. 212 e 226-227): minutos do mês = tosadores × jornada; cada atendimento
  consome o seu tempo mais a folga entre atendimentos. A demanda acima da
  capacidade é perdida, o "caso básico" do livro (p. 228). Utilização =
  atendimentos ÷ capacidade (p. 212-213); sem faixa de referência.
- Tempos do atendimento completo: informação de donos de pet shop repassada
  pelo professor (prática de mercado, sem fonte publicada); ponto médio de
  cada faixa. Folga de 10 a 15 minutos entre atendimentos (mesma origem).
- Preços de mercado: MercadoMineiro, 27 pet shops de Belo Horizonte, coleta
  em 13 e 14/10/2026 (divulgado pela Itatiaia em 19/10/2026).
- Insumos: planilha de precificação da Petisco (2026), prática de mercado.
- Mercado do serviço: razão entre serviços gerais e ração + produtos para
  cuidados no faturamento do setor pet (Abempet, 2025).
- Salário de referência do tosador: Novo Caged, CBO 5193-20 (compilação do
  Portal Salário, consultada em 23/11/2026), jornada de 43 h semanais.
"""

from __future__ import annotations

FONTE_TEMPOS = ("Informação de donos de pet shop repassada pelo professor em 23/11/2026 (prática de mercado, "
                "sem fonte publicada); ponto médio das faixas do atendimento completo")
FONTE_PRECOS = ("MercadoMineiro, pesquisa em 27 pet shops de Belo Horizonte, coleta em 13 e 14/10/2026 "
                "(divulgada pela Itatiaia em 19/10/2026)")
FONTE_INSUMOS = "Petisco, Calculadora de preço de banho e tosa (planilha, versão 1.0, 2026), aba Insumos por Serviço"
FONTE_MERCADO = ("Abempet, faturamento do setor pet em 2025: serviços gerais R$ 6,94 bi; ração R$ 41,41 bi; "
                 "produtos para cuidados R$ 4,63 bi (Folhapress, Diário do Comércio, 20/03/2026)")
FONTE_SALARIO = ("Novo Caged, CBO 5193-20 (tosador de animais domésticos), média de R$ 2.003,54 e jornada de "
                 "43 h semanais (últimos 12 meses, 06/2025 a 05/2026, 10.870 profissionais); compilação do "
                 "Portal Salário, consultada em 23/11/2026 "
                 "(https://www.salario.com.br/profissao/tosador-de-animais-domesticos-cbo-519320/)")

AVISO = ("Mercado do serviço estimado pela razão nacional entre serviços gerais (banho, tosa, passeador e outros) "
         "e mercadorias de pet shop: tende a superestimar o banho e tosa. A divisão da demanda em partes iguais "
         "entre os serviços é escolha de modelagem (sem fonte), e a elasticidade de preço (-2,62) vem de escolha de "
         "marca de produto (Bijmolt et al., 2005), aplicada aqui por extensão. Porte grande fora: sem preço com fonte.")

# Razão serviços gerais ÷ (ração + produtos para cuidados), Abempet 2025.
RAZAO_SERVICO = 6.94 / (41.41 + 4.63)

FOLGA_MIN = 12.5          # ponto médio de 10 a 15 minutos entre atendimentos
JORNADA_SEMANAL_H = 43.0  # Caged, CBO 5193-20
SALARIO_REFERENCIA = 2003.54

# id: (nome, porte, tipo, tempo do atendimento em minutos, preço de mercado, insumos)
SERVICOS = {
    "bt_maquina_pequeno": ("Banho + tosa na máquina, porte pequeno (até 10 kg)", "PEQUENO", "MAQUINA",
                           75.0, round((96.82 + 110.91) / 2, 2), 4.5 + 7.0),
    "bt_tesoura_pequeno": ("Banho + tosa na tesoura, porte pequeno (até 10 kg)", "PEQUENO", "TESOURA",
                           105.0, round((100.23 + 112.50) / 2, 2), 4.5 + 7.5),
    "bt_maquina_medio": ("Banho + tosa na máquina, porte médio (10 a 25 kg)", "MEDIO", "MAQUINA",
                         105.0, 126.59, 7.0 + 10.5),
    "bt_tesoura_medio": ("Banho + tosa na tesoura, porte médio (10 a 25 kg)", "MEDIO", "TESOURA",
                         135.0, 128.86, 7.0 + 11.0),
}


def catalogo() -> list[dict]:
    return [{"id": sid, "nome": nome, "porte": porte, "tipo": tipo, "tempo_min": tempo, "folga_min": FOLGA_MIN,
             "preco_mercado": preco, "insumos": insumos}
            for sid, (nome, porte, tipo, tempo, preco, insumos) in SERVICOS.items()]


def fontes() -> dict:
    return {"tempos": FONTE_TEMPOS, "precos": FONTE_PRECOS, "insumos": FONTE_INSUMOS, "mercado": FONTE_MERCADO,
            "salario": FONTE_SALARIO, "aviso": AVISO, "razao_servico": RAZAO_SERVICO,
            "jornada_semanal_h": JORNADA_SEMANAL_H, "salario_referencia": SALARIO_REFERENCIA}


def setor_tem_servico(setor: str | None) -> bool:
    return setor == "pet"


def ativo(plano: dict | None) -> bool:
    bt = (plano or {}).get("banho_tosa") or {}
    return bool(bt.get("oferece"))


def precos(plano: dict | None) -> dict[str, float]:
    """Preço praticado por serviço; sem preço informado vale o de mercado."""
    informados = ((plano or {}).get("banho_tosa") or {}).get("precos") or {}
    return {sid: float(informados.get(sid) or dados[4]) for sid, dados in SERVICOS.items()}


def atratividade(plano: dict | None, fator_propaganda: float = 1.0) -> float:
    """Média de (preço de mercado ÷ preço)^2,62 nos quatro serviços (mesma forma
    da atratividade da loja, Cooper e Nakanishi, 1988, p. 71-73)."""
    from .motor.simulacao import ELASTICIDADE_PRECO_ESCOLHA
    pr = precos(plano)
    termos = [(SERVICOS[sid][4] / pr[sid]) ** ELASTICIDADE_PRECO_ESCOLHA for sid in SERVICOS if pr[sid] > 0]
    return (sum(termos) / len(SERVICOS)) * fator_propaganda if termos else 0.0


def minutos_mes(tosadores: float, fracao_mes: float = 1.0) -> float:
    """Minutos de trabalho dos tosadores no período (jornada × 52 ÷ 12 semanas)."""
    return max(0.0, float(tosadores)) * JORNADA_SEMANAL_H * 52 / 12 * 60 * max(0.0, float(fracao_mes))


def apurar(plano: dict | None, demanda_reais: float, tosadores: float, fracao_mes: float = 1.0) -> dict:
    """Atendimentos, receita e insumos do mês. A demanda em reais é dividida em
    partes iguais entre os serviços e convertida em atendimentos pelo preço da
    loja; se os minutos pedidos passam da capacidade, todos os serviços são
    atendidos na mesma proporção e o restante é demanda perdida."""
    pr = precos(plano)
    parte = max(0.0, float(demanda_reais)) / len(SERVICOS)
    pedidos = {sid: (parte / pr[sid] if pr[sid] > 0 else 0.0) for sid in SERVICOS}
    minutos_pedidos = sum(q * (SERVICOS[sid][3] + FOLGA_MIN) for sid, q in pedidos.items())
    capacidade = minutos_mes(tosadores, fracao_mes)
    fracao = min(1.0, capacidade / minutos_pedidos) if minutos_pedidos > 0 else 0.0
    linhas, receita, insumos, usados = [], 0.0, 0.0, 0.0
    for sid, q in pedidos.items():
        feitos = int(q * fracao)  # atendimento inteiro
        nome, _porte, _tipo, tempo, preco_mercado, insumo = SERVICOS[sid]
        r = round(feitos * pr[sid], 2)
        i = round(feitos * insumo, 2)
        receita += r
        insumos += i
        usados += feitos * (tempo + FOLGA_MIN)
        linhas.append({"id": sid, "nome": nome, "preco": pr[sid], "preco_mercado": preco_mercado,
                       "pedidos": round(q, 2), "atendimentos": feitos, "receita": r, "insumos": i})
    perdidos = sum(l["pedidos"] - l["atendimentos"] for l in linhas)
    return {"linhas": linhas, "receita": round(receita, 2), "insumos": round(insumos, 2),
            "demanda_reais": round(float(demanda_reais), 2), "atendimentos": sum(l["atendimentos"] for l in linhas),
            "atendimentos_perdidos": round(perdidos, 2), "minutos_capacidade": round(capacidade, 1),
            "minutos_usados": round(usados, 1), "minutos_pedidos": round(minutos_pedidos, 1),
            "utilizacao": round(usados / capacidade, 4) if capacidade > 0 else None,
            "tosadores": float(tosadores), "fontes": fontes()}
