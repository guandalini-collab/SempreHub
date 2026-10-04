from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .events import EventEngine
from .models import (
    Base,
    Company,
    Employee,
    FaseAtual,
    GameSession,
    RegimeTributario,
)

DATABASE_URL = "sqlite:///./semprehub.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SempreHub Simulador")

# Constantes de balanceamento do simulador (regras de negócio 2026)
CUSTOS_FIXOS_ESTRUTURAIS_BASICOS = 3000.0
DEMANDA_BASE_MERCADO = 5000
PRECO_MEDIO_MERCADO = 100.0
INVESTIMENTO_ALTO_THRESHOLD = 10000.0
PENALIDADE_MEIO_DO_CAMINHO = 0.30
FATOR_CLT_SIMPLES = 1.45
FATOR_CLT_LUCRO_PRESUMIDO = 1.82
TAXA_MEI = 80.0
TETO_MEI_ESTOURO_20PCT = 97200.0
MULTA_DESENQUADRAMENTO_MEI = 5000.0
QUEDA_AUTOEFICACIA_CAIXA_NEGATIVO = 15.0
CMV_BASE_PERCENTUAL_FATURAMENTO = 0.40


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def root():
    return {"status": "ok", "service": "SempreHub Simulador API"}


@app.post("/partidas/{session_id}/avancar-turno")
async def avancar_turno(session_id: int, db: Session = Depends(get_db)):
    game_session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not game_session:
        raise HTTPException(status_code=404, detail="Sessão de jogo não encontrada")

    company = (
        db.query(Company)
        .filter(Company.game_session_id == game_session.id)
        .first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada para esta sessão")

    employees = db.query(Employee).filter(Employee.company_id == company.id).all()

    # 2. Custo Brasil da Folha (CLT)
    if company.regime_tributario in (RegimeTributario.MEI, RegimeTributario.SIMPLES_NACIONAL):
        fator_clt = FATOR_CLT_SIMPLES
    else:
        fator_clt = FATOR_CLT_LUCRO_PRESUMIDO

    custo_folha_total = sum(employee.salario_base * fator_clt for employee in employees)

    # 1. Verificação de Estado (Dornelas)
    custos_fixos_totais = custo_folha_total + CUSTOS_FIXOS_ESTRUTURAIS_BASICOS
    if game_session.caixa_atual < custos_fixos_totais:
        game_session.fase_atual = FaseAtual.SOBREVIVENCIA

    # 3. Algoritmo de Porter (Coerência Estratégica)
    investimento_luxo_pd = company.investimento_marketing + company.investimento_pd
    penalizado_porter = (
        company.preco_produto < PRECO_MEDIO_MERCADO
        and investimento_luxo_pd > INVESTIMENTO_ALTO_THRESHOLD
    )

    unidades_vendidas = DEMANDA_BASE_MERCADO
    if penalizado_porter:
        unidades_vendidas *= (1 - PENALIDADE_MEIO_DO_CAMINHO)

    faturamento_rodada = company.preco_produto * unidades_vendidas
    company.faturamento_acumulado_ano += faturamento_rodada

    # CMV da rodada, agravado pela greve de logística enquanto o efeito estiver ativo
    cmv_base_rodada = faturamento_rodada * CMV_BASE_PERCENTUAL_FATURAMENTO
    if company.cmv_turnos_restantes > 0:
        cmv_rodada = cmv_base_rodada * company.cmv_multiplicador
        company.cmv_turnos_restantes -= 1
        if company.cmv_turnos_restantes == 0:
            company.cmv_multiplicador = 1.0
    else:
        cmv_rodada = cmv_base_rodada

    # 4. Regra Fiscal do MEI
    imposto_rodada = 0.0
    desenquadrado_mei = False
    if company.regime_tributario == RegimeTributario.MEI:
        imposto_rodada = TAXA_MEI
        if company.faturamento_acumulado_ano > TETO_MEI_ESTOURO_20PCT:
            company.regime_tributario = RegimeTributario.SIMPLES_NACIONAL
            game_session.caixa_atual -= MULTA_DESENQUADRAMENTO_MEI
            desenquadrado_mei = True

    # 5. Atualização do caixa
    game_session.caixa_atual += (
        faturamento_rodada
        - custo_folha_total
        - CUSTOS_FIXOS_ESTRUTURAIS_BASICOS
        - imposto_rodada
        - company.investimento_marketing
        - company.investimento_pd
        - cmv_rodada
    )

    # 6. Atributos comportamentais
    if game_session.caixa_atual < 0:
        game_session.autoeficacia -= QUEDA_AUTOEFICACIA_CAIXA_NEGATIVO

    game_session.mes_atual += 1

    db.commit()
    db.refresh(game_session)
    db.refresh(company)

    # Sorteio de evento (Incerteza de Knight), no final do cálculo financeiro do turno
    event_engine = EventEngine(db)
    evento_sorteado = event_engine.processar_turno(game_session, company)

    return {
        "session_id": game_session.id,
        "mes_atual": game_session.mes_atual,
        "fase_atual": game_session.fase_atual.value,
        "caixa_atual": game_session.caixa_atual,
        "autoeficacia": game_session.autoeficacia,
        "necessidade_realizacao": game_session.necessidade_realizacao,
        "networking": game_session.networking,
        "empresa": {
            "regime_tributario": company.regime_tributario.value,
            "faturamento_acumulado_ano": company.faturamento_acumulado_ano,
            "desenquadrado_mei": desenquadrado_mei,
        },
        "demonstrativo": {
            "receitaBruta": faturamento_rodada,
            "custoPessoalClt": custo_folha_total,
            "custoCmv": cmv_rodada,
            "impostoPago": imposto_rodada,
        },
        "detalhes_rodada": {
            "unidades_vendidas": unidades_vendidas,
            "cmv_turnos_restantes": company.cmv_turnos_restantes,
            "penalizado_posicionamento_porter": penalizado_porter,
        },
        "evento": evento_sorteado,
    }
