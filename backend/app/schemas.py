"""Esquemas de entrada da API (validação dos dados enviados pelo navegador)."""

from typing import List, Optional

from pydantic import BaseModel, Field

from .models import CargoEquipe, ClasseDornelas, Papel, RegimeTributario, TipoEntradaGem


class CadastroEntrada(BaseModel):
    nome: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=200)
    senha: str = Field(min_length=8, max_length=128)
    papel: Papel = Papel.ALUNO
    codigo_docente: Optional[str] = None


class LoginEntrada(BaseModel):
    email: str
    senha: str


class EsqueciSenhaEntrada(BaseModel):
    email: str = Field(min_length=3, max_length=200)


class RedefinirSenhaEntrada(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    nova_senha: str = Field(min_length=8, max_length=128)


class AlunoTesteEntrada(BaseModel):
    nome: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=200)
    senha: str = Field(min_length=8, max_length=128)


class ParametrosTurma(BaseModel):
    modo_equipe: bool = False
    total_rodadas: int = Field(12, ge=1, le=60)
    caixa_inicial: float = Field(20000.0, ge=0)
    preco_referencia: float = Field(100.0, gt=0)
    custo_unitario: float = Field(40.0, ge=0)
    demanda_base_por_empresa: float = Field(220.0, gt=0)
    crescimento_mercado_mensal: float = Field(0.01, ge=-0.2, le=0.2)
    produtividade_por_pessoa: float = Field(120.0, gt=0)
    custos_fixos_mensais: float = Field(1500.0, ge=0)
    salario_base: float = Field(2000.0, ge=0)
    taxa_juros_mensal: float = Field(0.025, ge=0, le=0.5)
    taxa_cheque_especial: float = Field(0.08, ge=0, le=0.5)
    limite_credito: float = Field(50000.0, ge=0)
    probabilidade_evento: float = Field(0.35, ge=0, le=1)
    teto_mei_anual: float = Field(81000.0, gt=0)
    das_mei_mensal: float = Field(82.05, ge=0)
    aliquota_icms: float = Field(0.17, ge=0, le=0.4)


class TurmaEntrada(ParametrosTurma):
    nome: str = Field(min_length=3, max_length=120)


class FecharRodadaEntrada(BaseModel):
    evento: str = "SORTEAR"
    rodada: Optional[int] = Field(None, ge=1, le=60)


class EntrarTurmaEntrada(BaseModel):
    codigo: str = Field(min_length=4, max_length=12)
    nome_empresa: str = Field(min_length=2, max_length=120)
    tipo_entrada_gem: TipoEntradaGem
    classe_dornelas: ClasseDornelas
    regime_tributario: RegimeTributario = RegimeTributario.MEI


class DecisaoEntrada(BaseModel):
    versao: Optional[int] = Field(None, ge=0)
    rodada: Optional[int] = Field(None, ge=1, le=60)
    preco: float = Field(gt=0, le=100000)
    marketing: float = Field(0.0, ge=0, le=10_000_000)
    pd: float = Field(0.0, ge=0, le=10_000_000)
    networking: float = Field(0.0, ge=0, le=10_000_000)
    contratar: int = Field(0, ge=0, le=100)
    demitir: int = Field(0, ge=0, le=100)
    emprestimo: float = Field(0.0, ge=0, le=10_000_000)
    amortizacao: float = Field(0.0, ge=0, le=10_000_000)
    regime_solicitado: Optional[RegimeTributario] = None


class EntrarEquipeEntrada(BaseModel):
    codigo: str = Field(min_length=16, max_length=64)


class MembroEquipeEntrada(BaseModel):
    aluno_id: int = Field(gt=0)
    cargos: List[CargoEquipe] = Field(min_length=1, max_length=5)


class EquipeEntrada(BaseModel):
    membros: List[MembroEquipeEntrada] = Field(min_length=1, max_length=5)


class AprovarDecisaoEntrada(BaseModel):
    versao: int = Field(ge=1)
    rodada: Optional[int] = Field(None, ge=1, le=60)
