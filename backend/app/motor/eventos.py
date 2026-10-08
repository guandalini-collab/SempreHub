"""Eventos macroeconômicos (incerteza de Knight).

Os eventos atingem a turma inteira na mesma rodada, para que a competição seja justa.
O professor pode escolher o evento, sortear ou não aplicar nenhum.
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Evento:
    codigo: str
    titulo: str
    narrativa: str
    codigos: Tuple[str, ...] = ()

    def contem(self, codigo: str) -> bool:
        return codigo == self.codigo or codigo in self.codigos


NENHUM = Evento(
    "NENHUM",
    "Mês sem imprevistos",
    "O mês passa sem grandes sobressaltos macroeconômicos.",
)

EVENTOS: Dict[str, Evento] = {
    e.codigo: e
    for e in [
        Evento(
            "GREVE_LOGISTICA",
            "Greve na logística",
            "Uma greve nacional de caminhoneiros trava as rodovias e encarece o transporte de "
            "insumos. Nesta rodada e na próxima, o custo da mercadoria vendida (CMV) sobe 40%.",
        ),
        Evento(
            "NOTIFICACAO_FISCAL",
            "Notificação fiscal",
            "A Receita Federal intensifica a fiscalização sobre pequenas empresas. Empresas com "
            "rede de contatos (networking) abaixo de 30 não conseguem apoio contábil a tempo e "
            "pagam multa de R$ 3.500,00.",
        ),
        Evento(
            "ALTA_SELIC",
            "Alta da Selic",
            "O Banco Central eleva a taxa básica de juros para conter a inflação. Os juros dos "
            "empréstimos bancários sobem 0,5 ponto percentual ao mês a partir desta rodada.",
        ),
        Evento(
            "QUEDA_SELIC",
            "Queda da Selic",
            "Com a inflação controlada, o Banco Central reduz a taxa básica de juros. Os juros dos "
            "empréstimos bancários caem 0,5 ponto percentual ao mês a partir desta rodada.",
        ),
        Evento(
            "DEMANDA_AQUECIDA",
            "Demanda aquecida",
            "Uma data comemorativa e a melhora da renda das famílias aumentam o consumo. "
            "A demanda total do mercado cresce 25% nesta rodada.",
        ),
        Evento(
            "RETRACAO_ECONOMICA",
            "Retração econômica",
            "O desemprego sobe e as famílias cortam gastos. A demanda total do mercado cai 25% "
            "nesta rodada.",
        ),
    ]
}

MULTA_NOTIFICACAO_FISCAL = 3500.0
NETWORKING_MINIMO_DEFESA_FISCAL = 30.0
AUMENTO_CMV_GREVE = 0.40
DURACAO_GREVE_RODADAS = 2
VARIACAO_SELIC = 0.005
VARIACAO_DEMANDA = 0.25
TAXA_JUROS_MINIMA = 0.005


def opcoes_evento() -> List[Dict[str, str]]:
    return [{"codigo": e.codigo, "titulo": e.titulo, "narrativa": e.narrativa} for e in EVENTOS.values()]


def escolher_evento(escolha: str, probabilidade: float, rng: Optional[random.Random] = None) -> Evento:
    """Sorteia até três eventos compatíveis, ou aplica uma escolha explícita."""
    rng = rng or random.Random()
    if escolha == "NENHUM":
        return NENHUM
    if escolha == "SORTEAR":
        if rng.random() >= probabilidade:
            return NENHUM
        grupos = [
            ["GREVE_LOGISTICA"], ["NOTIFICACAO_FISCAL"],
            ["ALTA_SELIC", "QUEDA_SELIC"],
            ["DEMANDA_AQUECIDA", "RETRACAO_ECONOMICA"],
        ]
        selecionados = [EVENTOS[rng.choice(grupo)] for grupo in rng.sample(grupos, rng.randint(1, 3))]
        if len(selecionados) == 1:
            return selecionados[0]
        return Evento(
            "MULTIPLOS", " + ".join(e.titulo for e in selecionados),
            "\n\n".join(e.narrativa for e in selecionados),
            tuple(e.codigo for e in selecionados),
        )
    if escolha not in EVENTOS:
        raise ValueError(f"Evento desconhecido: {escolha}")
    return EVENTOS[escolha]
