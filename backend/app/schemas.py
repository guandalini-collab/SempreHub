"""Esquemas de entrada da API (validação dos dados enviados pelo navegador)."""

from math import isclose
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class ConfiguracaoSimulacao(BaseModel):
    """Parâmetros didáticos dos motores avançados, congelados ao iniciar o jogo."""

    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")

    capacidade_maquina: int = Field(240, ge=1, le=100_000)
    preco_maquina: float = Field(12000.0, gt=0, le=10_000_000)
    vida_util_maquina: int = Field(24, ge=1, le=600)
    custo_frete_km: float = Field(0.1, ge=0, le=1000)
    custo_armazenagem: float = Field(0.01, ge=0, le=1)
    frete_rapido: float = Field(15.0, ge=0, le=100_000)
    frete_padrao: float = Field(10.0, ge=0, le=100_000)
    frete_economico: float = Field(5.0, ge=0, le=100_000)
    custo_nuvem_cliente: float = Field(10.0, ge=0, le=100_000)
    churn_base: float = Field(0.05, ge=0, le=1)
    aliquota_servico: float = Field(
        0.06, ge=0, le=1,
        description="Alíquota didática para serviços; não representa enquadramento fiscal real.",
    )
    concorrentes_virtuais: int = Field(0, ge=0, le=200)
    nivel_concorrencia: Literal["BAIXA", "MEDIA", "ALTA"] = "MEDIA"
    estrutura_mercado: Literal["MONOPOLIO", "OLIGOPOLIO", "MONOPOLISTICA", "PERFEITA", "FRAGMENTADO"] = "FRAGMENTADO"
    forca_concorrentes: Literal["FRACA", "MEDIA", "FORTE", "MUITO_FORTE"] = "MEDIA"
    peso_lucro: float = Field(0.4, ge=0, le=1)
    peso_patrimonio: float = Field(0.3, ge=0, le=1)
    peso_satisfacao: float = Field(0.2, ge=0, le=1)
    peso_participacao: float = Field(0.1, ge=0, le=1)

    @model_validator(mode="after")
    def validar_pesos(self):
        total = self.peso_lucro + self.peso_patrimonio + self.peso_satisfacao + self.peso_participacao
        if not isclose(total, 1.0, rel_tol=0, abs_tol=1e-6):
            raise ValueError("Os pesos dos indicadores pedagógicos devem somar 1.")
        return self


class PontoCentroGravidade(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    nome: str = Field("", max_length=100)
    x: float = Field(0, ge=-1_000_000, le=1_000_000)
    y: float = Field(0, ge=-1_000_000, le=1_000_000)
    volume: float = Field(0, ge=0, le=1_000_000)


class EstudoCentroGravidade(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    pontos: list[PontoCentroGravidade] = Field(default_factory=list, max_length=20)
    local_x: Optional[float] = Field(None, ge=-1_000_000, le=1_000_000)
    local_y: Optional[float] = Field(None, ge=-1_000_000, le=1_000_000)
    justificativa: str = Field("", max_length=2000)


class DecisaoSimulacao(BaseModel):
    """Produção/logística no modo tradicional e clientes/capital no modo startup.

    Salário, benefícios, treinamento, prazos e posicionamento valem para ambos.
    Compras de máquinas ativam capacidade somente na rodada seguinte. Aporte e
    valuation são exclusivos de startup e não integram a receita da empresa.
    """

    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")

    centro_gravidade: Optional[EstudoCentroGravidade] = None
    producao: int = Field(0, ge=0, le=1_000_000)
    comprar_mp: int = Field(0, ge=0, le=1_000_000)
    horas_extras: float = Field(0.0, ge=0, le=40, description="Horas opcionais por empregado no mês; premissa didática.")
    comprar_maquinas: int = Field(0, ge=0, le=100)
    manutencao: float = Field(0.0, ge=0, le=10_000_000)
    modal: Literal["RAPIDO", "PADRAO", "ECONOMICO"] = "PADRAO"
    salario: Optional[float] = Field(None, ge=0, le=1_000_000)
    beneficio: float = Field(0.0, ge=0, le=1_000_000)
    treinamento: float = Field(0.0, ge=0, le=10_000_000)
    vendas_prazo: float = Field(0.0, ge=0, le=1)
    prazo_recebimento: int = Field(1, ge=1, le=3)
    compras_prazo: float = Field(0.0, ge=0, le=1)
    prazo_pagamento: int = Field(1, ge=1, le=3)
    posicionamento: Literal["CUSTO", "DIFERENCIACAO"] = "CUSTO"
    canal: Literal["DIRETO", "DISTRIBUIDOR", "DIGITAL"] = "DIRETO"
    marketing_digital: float = Field(0.0, ge=0, le=10_000_000)
    capacidade_nuvem: int = Field(300, ge=0, le=1_000_000)
    aporte: float = Field(0.0, ge=0, le=10_000_000)
    valuation: float = Field(100000.0, gt=0, le=1_000_000_000)


class ParametrosTurma(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    modo_equipe: bool = False
    modo_jogo: Literal["LEGADO", "TRADICIONAL", "STARTUP"] = "LEGADO"
    cenario: Literal["ZERO", "CRISE"] = "ZERO"
    configuracao_simulacao: ConfiguracaoSimulacao = Field(default_factory=ConfiguracaoSimulacao)
    total_rodadas: int = Field(12, ge=1, le=60)
    caixa_inicial: float = Field(20000.0, ge=0, le=10_000_000)
    preco_referencia: float = Field(100.0, gt=0, le=100_000)
    custo_unitario: float = Field(40.0, ge=0, le=100_000)
    demanda_base_por_empresa: float = Field(220.0, gt=0, le=1_000_000)
    crescimento_mercado_mensal: float = Field(0.01, ge=-0.2, le=0.2)
    produtividade_por_pessoa: float = Field(120.0, gt=0, le=100_000)
    custos_fixos_mensais: float = Field(1500.0, ge=0, le=10_000_000)
    salario_base: float = Field(2000.0, ge=0, le=1_000_000)
    taxa_juros_mensal: float = Field(0.025, ge=0, le=0.5)
    taxa_cheque_especial: float = Field(0.08, ge=0, le=0.5)
    limite_credito: float = Field(50000.0, ge=0, le=10_000_000)
    probabilidade_evento: float = Field(0.35, ge=0, le=1)
    teto_mei_anual: float = Field(81000.0, gt=0, le=10_000_000)
    das_mei_mensal: float = Field(82.05, ge=0, le=100_000)
    aliquota_icms: float = Field(0.17, ge=0, le=0.4)


class TurmaEntrada(ParametrosTurma):
    nome: str = Field(min_length=1, max_length=120)


class FecharRodadaEntrada(BaseModel):
    forcar: bool = False
    evento: str = "SORTEAR"
    rodada: Optional[int] = Field(None, ge=1, le=60)


class EntrarTurmaEntrada(BaseModel):
    turma_id: Optional[int] = Field(None, gt=0)
    codigo: Optional[str] = Field(None, min_length=4, max_length=12)
    nome_empresa: str = Field(min_length=2, max_length=120)
    tipo_entrada_gem: TipoEntradaGem
    classe_dornelas: ClasseDornelas
    regime_tributario: RegimeTributario = RegimeTributario.MEI


class AlocacaoMidia(BaseModel):
    id: str = Field(max_length=80)
    quantidade: int = Field(ge=1, le=1000000)

class ItensAnalise(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SWOTAnalise(ItensAnalise):
    forcas: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    fraquezas: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    oportunidades: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    ameacas: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    diretriz: Optional[Literal["PRECO", "QUALIDADE", "INOVACAO"]] = None


class ForcaAnalise(ItensAnalise):
    intensidade: Optional[int] = Field(None, ge=1, le=10)
    justificativa: str = Field("", max_length=2000)


class PorterAnalise(ItensAnalise):
    rivalidade: ForcaAnalise = Field(default_factory=ForcaAnalise)
    fornecedores: ForcaAnalise = Field(default_factory=ForcaAnalise)
    compradores: ForcaAnalise = Field(default_factory=ForcaAnalise)
    entrantes: ForcaAnalise = Field(default_factory=ForcaAnalise)
    substitutos: ForcaAnalise = Field(default_factory=ForcaAnalise)


class ProdutoBCG(ItensAnalise):
    produto_id: str = Field(min_length=1, max_length=80)
    nome: str = Field(min_length=1, max_length=200)
    crescimento: float = Field(ge=-100, le=1000)
    participacao: float = Field(ge=0, le=100)
    classificacao: Literal["ESTRELA", "VACA", "INTERROGACAO", "ABACAXI"]
    base: Literal["DADO", "PROJECAO"] = "DADO"
    premissas: str = Field("", max_length=2000)


class PESTELAnalise(ItensAnalise):
    politico: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    economico: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    social: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    tecnologico: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    ambiental: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    legal: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    juros_previstos: Optional[float] = Field(None, ge=0, le=100)


class SegmentacaoAnalise(ItensAnalise):
    demografica: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    geografica: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    psicografica: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    comportamental: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    porte: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    setor: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    compras: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=20)
    preco_maximo: Optional[float] = Field(None, gt=0, le=1000000)
    cobertura: Optional[Literal["LOCAL", "REGIONAL", "NACIONAL", "INTERNACIONAL"]] = None
    canais: list[Literal["VAREJO", "ECOMMERCE", "MARKETPLACE", "ATACADO", "FRANQUIA", "DIRETO"]] = Field(default_factory=list, max_length=6)
    midias: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(default_factory=list, max_length=80)


class AnalisesEstrategicas(ItensAnalise):
    diagnostico_automatico: bool = False
    versao: Literal[1] = 1
    swot: SWOTAnalise = Field(default_factory=SWOTAnalise)
    porter: PorterAnalise = Field(default_factory=PorterAnalise)
    bcg: list[ProdutoBCG] = Field(default_factory=list, max_length=20)
    pestel: PESTELAnalise = Field(default_factory=PESTELAnalise)
    segmentacao: SegmentacaoAnalise = Field(default_factory=SegmentacaoAnalise)


class ServicoCotado(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    midia_id: str = Field(min_length=1, max_length=80)
    valor: float = Field(ge=0.01, le=10_000_000)
    fonte_url: str = Field(min_length=8, max_length=2000, pattern=r"^https?://[^\s]+$")


class MixProduto(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    produto_id: str = Field(min_length=1, max_length=80)
    preco: float = Field(gt=0, le=100000)
    peso: float = Field(gt=0, le=100)
    revisado: bool = False
    estrategia_preco: Literal["PENETRACAO", "COMPETITIVO", "DESNATAMENTO", "VALOR"]
    posicionamento: Literal["QUALIDADE", "PRECO", "INOVACAO"]
    canais: list[Literal["VAREJO", "ECOMMERCE", "MARKETPLACE", "ATACADO", "FRANQUIA", "DIRETO"]] = Field(min_length=1, max_length=6)
    cobertura: Literal["LOCAL", "REGIONAL", "NACIONAL", "INTERNACIONAL"]
    intensidade: Literal["BAIXA", "MEDIA", "ALTA", "INTENSIVA"]
    servicos: list[AlocacaoMidia] = Field(default_factory=list, max_length=160)
    servicos_cotados: list[ServicoCotado] = Field(default_factory=list, max_length=80)
    custos_campanha: Optional[dict] = None
    midias: list[AlocacaoMidia] = Field(default_factory=list, max_length=80)
    custo_unitario: Optional[float] = Field(None, gt=0, le=1000000)
    produto_nome: Optional[str] = Field(None, max_length=200)


class PlanoComercial(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    versao_custos: Literal[2] = 2
    custos_campanha: Optional[dict] = None
    edicao_id: int = Field(gt=0)
    produtos: list[MixProduto] = Field(default_factory=list, max_length=10)
    produto_id: str = Field(max_length=80)
    estrategia_preco: Literal["PENETRACAO", "COMPETITIVO", "DESNATAMENTO", "VALOR"]
    posicionamento: Literal["QUALIDADE", "PRECO", "INOVACAO"]
    canais: list[Literal["VAREJO", "ECOMMERCE", "MARKETPLACE", "ATACADO", "FRANQUIA", "DIRETO"]] = Field(min_length=1, max_length=6)
    cobertura: Literal["LOCAL", "REGIONAL", "NACIONAL", "INTERNACIONAL"]
    intensidade: Literal["BAIXA", "MEDIA", "ALTA", "INTENSIVA"]
    midias: list[AlocacaoMidia] = Field(default_factory=list, max_length=80)
    estrategias: dict[str, str] = Field(default_factory=dict)
    analises: Optional[AnalisesEstrategicas] = None
    custo_unitario: Optional[float] = Field(None, gt=0, le=1000000)
    produto_nome: Optional[str] = Field(None, max_length=200)

class DecisaoEntrada(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    versao: Optional[int] = Field(None, ge=0)
    rodada: Optional[int] = Field(None, ge=1, le=60)
    rascunho: bool = False
    analise_financeira: str = Field("", max_length=6000)
    revisao_areas: dict[Literal["decisoes", "financas", "producao", "logistica"], bool] = Field(default_factory=dict)
    preco: float = Field(gt=0, le=100000)
    marketing: float = Field(0.0, ge=0, le=10_000_000)
    pd: float = Field(0.0, ge=0, le=10_000_000)
    networking: float = Field(0.0, ge=0, le=10_000_000)
    contratar: int = Field(0, ge=0, le=100)
    demitir: int = Field(0, ge=0, le=100)
    emprestimo: float = Field(0.0, ge=0, le=10_000_000)
    amortizacao: float = Field(0.0, ge=0, le=10_000_000)
    regime_solicitado: Optional[RegimeTributario] = None
    simulacao: Optional[DecisaoSimulacao] = None
    plano_comercial: Optional[PlanoComercial] = None

    @model_validator(mode="after")
    def validar_marketing_digital(self):
        if self.simulacao is not None and self.simulacao.marketing_digital > self.marketing:
            raise ValueError("O marketing digital deve ser parte do investimento total em marketing.")
        return self


class EntrarEquipeEntrada(BaseModel):
    empresa_id: Optional[int] = Field(None, gt=0)
    codigo: Optional[str] = Field(None, min_length=16, max_length=64)


class MembroEquipeEntrada(BaseModel):
    aluno_id: int = Field(gt=0)
    cargos: List[CargoEquipe] = Field(min_length=1, max_length=5)


class EquipeEntrada(BaseModel):
    membros: List[MembroEquipeEntrada] = Field(min_length=1, max_length=5)


class AprovarDecisaoEntrada(BaseModel):
    versao: int = Field(ge=1)
    rodada: Optional[int] = Field(None, ge=1, le=60)
