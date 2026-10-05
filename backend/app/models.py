"""Modelos de dados do SempreHub.

Estrutura geral:
- Usuario: aluno ou professor.
- Turma: criada pelo professor; reúne as empresas que disputam o mesmo mercado.
- Empresa: a empresa de um aluno dentro de uma turma.
- Decisao: o que o aluno decidiu para uma rodada (mês).
- Resultado: o que aconteceu com a empresa ao fechar a rodada.
- EventoRodada: o evento macroeconômico (incerteza de Knight) aplicado à turma na rodada.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def agora() -> datetime:
    """Data e hora em UTC, sem fuso (compatível com SQLite e PostgreSQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Papel(str, enum.Enum):
    ALUNO = "ALUNO"
    PROFESSOR = "PROFESSOR"


class FaseAtual(str, enum.Enum):
    """Fases inspiradas no ciclo empreendedor descrito por Dornelas."""

    IDEACAO = "IDEACAO"
    PLANEJAMENTO = "PLANEJAMENTO"
    CAPTACAO = "CAPTACAO"
    OPERACAO_ESTAVEL = "OPERACAO_ESTAVEL"
    SOBREVIVENCIA = "SOBREVIVENCIA"


class TipoEntradaGem(str, enum.Enum):
    """Motivação para empreender, conforme a tipologia do GEM."""

    NECESSIDADE = "NECESSIDADE"
    OPORTUNIDADE = "OPORTUNIDADE"


class ClasseDornelas(str, enum.Enum):
    SERIAL = "SERIAL"
    FRANQUIA = "FRANQUIA"
    CORPORATIVO = "CORPORATIVO"
    SOCIAL = "SOCIAL"


class RegimeTributario(str, enum.Enum):
    MEI = "MEI"
    SIMPLES_NACIONAL = "SIMPLES_NACIONAL"
    LUCRO_PRESUMIDO = "LUCRO_PRESUMIDO"


class StatusTurma(str, enum.Enum):
    ABERTA = "ABERTA"
    ENCERRADA = "ENCERRADA"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(200), nullable=False, unique=True, index=True)
    senha_hash = Column(String(300), nullable=False)
    papel = Column(Enum(Papel), nullable=False)
    criado_em = Column(DateTime, default=agora)

    turmas = relationship("Turma", back_populates="professor")
    empresas = relationship("Empresa", back_populates="aluno")


class Turma(Base):
    __tablename__ = "turmas"

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    codigo = Column(String(12), nullable=False, unique=True, index=True)
    professor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    status = Column(Enum(StatusTurma), nullable=False, default=StatusTurma.ABERTA)
    rodada_atual = Column(Integer, nullable=False, default=1)
    total_rodadas = Column(Integer, nullable=False, default=12)
    criado_em = Column(DateTime, default=agora)

    # Parâmetros de mercado e de custos (ajustáveis pelo professor antes da 1ª rodada)
    caixa_inicial = Column(Float, nullable=False, default=20000.0)
    preco_referencia = Column(Float, nullable=False, default=100.0)
    custo_unitario = Column(Float, nullable=False, default=40.0)
    demanda_base_por_empresa = Column(Float, nullable=False, default=220.0)
    crescimento_mercado_mensal = Column(Float, nullable=False, default=0.01)
    produtividade_por_pessoa = Column(Float, nullable=False, default=120.0)
    custos_fixos_mensais = Column(Float, nullable=False, default=1500.0)
    salario_base = Column(Float, nullable=False, default=2000.0)
    taxa_juros_mensal = Column(Float, nullable=False, default=0.025)
    taxa_cheque_especial = Column(Float, nullable=False, default=0.08)
    limite_credito = Column(Float, nullable=False, default=50000.0)
    probabilidade_evento = Column(Float, nullable=False, default=0.35)
    teto_mei_anual = Column(Float, nullable=False, default=81000.0)
    das_mei_mensal = Column(Float, nullable=False, default=82.05)
    aliquota_icms = Column(Float, nullable=False, default=0.17)

    # Estado macroeconômico persistente (efeitos de eventos que duram mais de uma rodada)
    cmv_multiplicador = Column(Float, nullable=False, default=1.0)
    cmv_rodadas_restantes = Column(Integer, nullable=False, default=0)

    professor = relationship("Usuario", back_populates="turmas")
    empresas = relationship("Empresa", back_populates="turma", order_by="Empresa.id")
    eventos = relationship("EventoRodada", back_populates="turma", order_by="EventoRodada.rodada")


class Empresa(Base):
    __tablename__ = "empresas"
    __table_args__ = (UniqueConstraint("turma_id", "aluno_id", name="uq_empresa_turma_aluno"),)

    id = Column(Integer, primary_key=True)
    turma_id = Column(Integer, ForeignKey("turmas.id"), nullable=False, index=True)
    aluno_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    nome = Column(String(120), nullable=False)
    criado_em = Column(DateTime, default=agora)

    # Perfil empreendedor
    tipo_entrada_gem = Column(Enum(TipoEntradaGem), nullable=False)
    classe_dornelas = Column(Enum(ClasseDornelas), nullable=False)
    autoeficacia = Column(Float, nullable=False, default=50.0)
    necessidade_realizacao = Column(Float, nullable=False, default=50.0)
    networking = Column(Float, nullable=False, default=20.0)
    fase_atual = Column(Enum(FaseAtual), nullable=False, default=FaseAtual.IDEACAO)

    # Situação econômica
    regime_tributario = Column(Enum(RegimeTributario), nullable=False)
    regime_pretendido = Column(Enum(RegimeTributario), nullable=True)
    caixa = Column(Float, nullable=False, default=0.0)
    divida = Column(Float, nullable=False, default=0.0)
    funcionarios = Column(Integer, nullable=False, default=0)
    marca = Column(Float, nullable=False, default=0.0)
    qualidade = Column(Float, nullable=False, default=0.0)
    faturamento_ano = Column(Float, nullable=False, default=0.0)
    das_mei_pago_ano = Column(Float, nullable=False, default=0.0)

    turma = relationship("Turma", back_populates="empresas")
    aluno = relationship("Usuario", back_populates="empresas")
    decisoes = relationship("Decisao", back_populates="empresa", order_by="Decisao.rodada")
    resultados = relationship("Resultado", back_populates="empresa", order_by="Resultado.rodada")


class Decisao(Base):
    __tablename__ = "decisoes"
    __table_args__ = (UniqueConstraint("empresa_id", "rodada", name="uq_decisao_empresa_rodada"),)

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    rodada = Column(Integer, nullable=False)

    preco = Column(Float, nullable=False)
    marketing = Column(Float, nullable=False, default=0.0)
    pd = Column(Float, nullable=False, default=0.0)
    networking = Column(Float, nullable=False, default=0.0)
    contratar = Column(Integer, nullable=False, default=0)
    demitir = Column(Integer, nullable=False, default=0)
    emprestimo = Column(Float, nullable=False, default=0.0)
    amortizacao = Column(Float, nullable=False, default=0.0)
    regime_solicitado = Column(Enum(RegimeTributario), nullable=True)
    automatica = Column(Integer, nullable=False, default=0)  # 1 = repetida pelo sistema
    enviada_em = Column(DateTime, default=agora, onupdate=agora)

    empresa = relationship("Empresa", back_populates="decisoes")


class Resultado(Base):
    __tablename__ = "resultados"
    __table_args__ = (UniqueConstraint("empresa_id", "rodada", name="uq_resultado_empresa_rodada"),)

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    rodada = Column(Integer, nullable=False)

    # Mercado
    preco = Column(Float, nullable=False)
    demanda = Column(Float, nullable=False)
    capacidade = Column(Float, nullable=False)
    unidades_vendidas = Column(Float, nullable=False)
    participacao_mercado = Column(Float, nullable=False)

    # Demonstrativo de resultado (DRE)
    receita = Column(Float, nullable=False)
    impostos = Column(Float, nullable=False)
    cmv = Column(Float, nullable=False)
    folha = Column(Float, nullable=False)
    custos_fixos = Column(Float, nullable=False)
    marketing = Column(Float, nullable=False)
    pd = Column(Float, nullable=False)
    networking_invest = Column(Float, nullable=False)
    rescisoes = Column(Float, nullable=False)
    royalties = Column(Float, nullable=False, default=0.0)
    juros = Column(Float, nullable=False)
    multas = Column(Float, nullable=False)
    lucro_liquido = Column(Float, nullable=False)

    # Situação ao final da rodada
    caixa_final = Column(Float, nullable=False)
    divida_final = Column(Float, nullable=False)
    regime = Column(Enum(RegimeTributario), nullable=False)
    aliquota_efetiva = Column(Float, nullable=False, default=0.0)
    funcionarios = Column(Integer, nullable=False)
    marca = Column(Float, nullable=False)
    qualidade = Column(Float, nullable=False)
    autoeficacia = Column(Float, nullable=False)
    networking = Column(Float, nullable=False)
    necessidade_realizacao = Column(Float, nullable=False)
    fase = Column(Enum(FaseAtual), nullable=False)

    alertas = Column(JSON, nullable=False, default=list)
    criado_em = Column(DateTime, default=agora)

    empresa = relationship("Empresa", back_populates="resultados")


class EventoRodada(Base):
    __tablename__ = "eventos_rodada"
    __table_args__ = (UniqueConstraint("turma_id", "rodada", name="uq_evento_turma_rodada"),)

    id = Column(Integer, primary_key=True)
    turma_id = Column(Integer, ForeignKey("turmas.id"), nullable=False, index=True)
    rodada = Column(Integer, nullable=False)
    codigo = Column(String(40), nullable=False)
    titulo = Column(String(120), nullable=False)
    narrativa = Column(String(1000), nullable=False)
    criado_em = Column(DateTime, default=agora)

    turma = relationship("Turma", back_populates="eventos")
