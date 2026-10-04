import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class FaseAtual(enum.Enum):
    IDEACAO = "IDEACAO"
    PLANEJAMENTO = "PLANEJAMENTO"
    CAPTACAO = "CAPTACAO"
    OPERACAO_ESTAVEL = "OPERACAO_ESTAVEL"
    SOBREVIVENCIA = "SOBREVIVENCIA"


class TipoEntradaGem(enum.Enum):
    NECESSIDADE = "NECESSIDADE"
    OPORTUNIDADE = "OPORTUNIDADE"


class ClasseDornelas(enum.Enum):
    SERIAL = "SERIAL"
    FRANQUIA = "FRANQUIA"
    CORPORATIVO = "CORPORATIVO"
    SOCIAL = "SOCIAL"


class RegimeTributario(enum.Enum):
    MEI = "MEI"
    SIMPLES_NACIONAL = "SIMPLES_NACIONAL"
    LUCRO_PRESUMIDO = "LUCRO_PRESUMIDO"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    game_sessions = relationship("GameSession", back_populates="user")


class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    fase_atual = Column(Enum(FaseAtual), nullable=False)
    tipo_entrada_gem = Column(Enum(TipoEntradaGem), nullable=False)
    classe_dornelas = Column(Enum(ClasseDornelas), nullable=False)

    mes_atual = Column(Integer, default=0)
    caixa_atual = Column(Float, default=0.0)
    autoeficacia = Column(Float, default=0.0)
    necessidade_realizacao = Column(Float, default=0.0)
    networking = Column(Float, default=0.0)

    user = relationship("User", back_populates="game_sessions")
    companies = relationship("Company", back_populates="game_session")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    game_session_id = Column(Integer, ForeignKey("game_sessions.id"), nullable=False)

    name = Column(String, nullable=False)
    regime_tributario = Column(Enum(RegimeTributario), nullable=False)
    preco_produto = Column(Float, default=0.0)
    investimento_marketing = Column(Float, default=0.0)
    investimento_pd = Column(Float, default=0.0)
    faturamento_acumulado_ano = Column(Float, default=0.0)

    # Estado persistido pelo EventEngine (eventos com efeito em turnos seguintes)
    cmv_multiplicador = Column(Float, default=1.0)
    cmv_turnos_restantes = Column(Integer, default=0)
    emprestimo_pj_ativo = Column(Boolean, default=False)
    taxa_juros_emprestimo_pj = Column(Float, default=0.0)

    game_session = relationship("GameSession", back_populates="companies")
    employees = relationship("Employee", back_populates="company")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    role = Column(String, nullable=False)
    salario_base = Column(Float, default=0.0)
    nivel_competencia = Column(Float, default=0.0)
    estresse = Column(Float, default=0.0)

    company = relationship("Company", back_populates="employees")
