import random
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from .models import Company, FaseAtual, GameSession


class EventEngine:
    """Motor de Incerteza de Knight: sorteia imprevistos macroeconômicos brasileiros."""

    EVENTOS = ["GREVE_LOGISTICA", "NOTIFICACAO_FISCAL", "MUDANCA_SELIC"]

    PROBABILIDADE_BASE_EVENTO_NEGATIVO = 0.30
    NETWORKING_MINIMO_CONTADORES = 30
    MULTA_NOTIFICACAO_FISCAL = 3500.0
    AUMENTO_CMV_GREVE = 0.40
    DURACAO_CMV_GREVE_TURNOS = 2
    AUMENTO_JUROS_SELIC = 0.25

    def __init__(self, db: Session):
        self.db = db

    def sortear_evento(self, game_session: GameSession) -> Optional[str]:
        probabilidade = self.PROBABILIDADE_BASE_EVENTO_NEGATIVO
        if game_session.fase_atual == FaseAtual.SOBREVIVENCIA:
            probabilidade *= 2

        if random.random() > probabilidade:
            return None
        return random.choice(self.EVENTOS)

    def processar_turno(self, game_session: GameSession, company: Company) -> Dict[str, Any]:
        evento = self.sortear_evento(game_session)

        if evento is None:
            return {
                "titulo": "Nenhum Imprevisto",
                "narrativa": "O mês passa sem grandes sobressaltos macroeconômicos.",
                "consequencias": {},
            }

        handlers = {
            "GREVE_LOGISTICA": self._evento_greve_logistica,
            "NOTIFICACAO_FISCAL": self._evento_notificacao_fiscal,
            "MUDANCA_SELIC": self._evento_mudanca_selic,
        }
        return handlers[evento](game_session, company)

    def _evento_greve_logistica(self, game_session: GameSession, company: Company) -> Dict[str, Any]:
        company.cmv_multiplicador = 1 + self.AUMENTO_CMV_GREVE
        company.cmv_turnos_restantes = self.DURACAO_CMV_GREVE_TURNOS

        self.db.commit()
        self.db.refresh(company)

        return {
            "titulo": "Greve na Logística",
            "narrativa": (
                "Uma greve nacional de caminhoneiros trava as rodovias brasileiras e "
                "encarece o transporte de insumos. Pelos próximos 2 turnos, o Custo da "
                "Mercadoria Vendida (CMV) da sua empresa sobe 40%."
            ),
            "consequencias": {
                "company_id": company.id,
                "cmv_multiplicador": company.cmv_multiplicador,
                "cmv_turnos_restantes": company.cmv_turnos_restantes,
            },
        }

    def _evento_notificacao_fiscal(self, game_session: GameSession, company: Company) -> Dict[str, Any]:
        multa_aplicada = 0.0

        if game_session.networking < self.NETWORKING_MINIMO_CONTADORES:
            multa_aplicada = self.MULTA_NOTIFICACAO_FISCAL
            game_session.caixa_atual -= multa_aplicada
            self.db.commit()
            self.db.refresh(game_session)
            narrativa = (
                "A Receita Federal identifica uma inconsistência contábil de anos "
                "anteriores. Sem uma rede de contadores de confiança para orientar a "
                "defesa, a empresa não consegue contestar a autuação e paga uma multa "
                "imediata de R$ 3.500,00."
            )
        else:
            narrativa = (
                "A Receita Federal identifica uma inconsistência contábil de anos "
                "anteriores, mas a rede de contatos com contadores (Networking) da sua "
                "empresa foi suficiente para regularizar a pendência sem multa."
            )

        return {
            "titulo": "Notificação Fiscal",
            "narrativa": narrativa,
            "consequencias": {
                "game_session_id": game_session.id,
                "multa_aplicada": multa_aplicada,
                "caixa_atual": game_session.caixa_atual,
            },
        }

    def _evento_mudanca_selic(self, game_session: GameSession, company: Company) -> Dict[str, Any]:
        if company.emprestimo_pj_ativo:
            company.taxa_juros_emprestimo_pj *= (1 + self.AUMENTO_JUROS_SELIC)
            self.db.commit()
            self.db.refresh(company)
            narrativa = (
                "O Banco Central eleva a taxa básica de juros (Selic) para conter a "
                "inflação. Como reflexo direto, a linha de empréstimo PJ ativa da sua "
                "empresa fica 25% mais cara."
            )
        else:
            narrativa = (
                "O Banco Central eleva a taxa básica de juros (Selic) para conter a "
                "inflação. Sua empresa não possui empréstimo PJ ativo no momento, então "
                "não há impacto direto no caixa desta rodada."
            )

        return {
            "titulo": "Mudança na Selic",
            "narrativa": narrativa,
            "consequencias": {
                "company_id": company.id,
                "emprestimo_pj_ativo": company.emprestimo_pj_ativo,
                "taxa_juros_emprestimo_pj": company.taxa_juros_emprestimo_pj,
            },
        }
