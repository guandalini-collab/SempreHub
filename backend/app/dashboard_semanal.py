"""Indicadores de análise: bases manuais nunca alteram decisões, notas ou contabilidade."""
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional
from .models import Resultado, ObservacaoSemanal
from fastapi import HTTPException


class BasesSemanais(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    marketing: Optional[float]=Field(None,ge=0,le=1e9)
    novos_clientes: Optional[int]=Field(None,ge=0,le=100000000)
    pedidos: Optional[int]=Field(None,ge=0,le=100000000)
    leads: Optional[int]=Field(None,ge=0,le=100000000)
    cliques: Optional[int]=Field(None,ge=0,le=100000000)
    cancelamentos: Optional[int]=Field(None,ge=0,le=100000000)
    base_recorrentes: Optional[int]=Field(None,ge=0,le=100000000)
    promotores: Optional[int]=Field(None,ge=0,le=100000000)
    neutros: Optional[int]=Field(None,ge=0,le=100000000)
    detratores: Optional[int]=Field(None,ge=0,le=100000000)
    horas_ausencia: Optional[float]=Field(None,ge=0,le=1e8)
    horas_contratadas: Optional[float]=Field(None,ge=0,le=1e8)
    picking_minutos: Optional[float]=Field(None,ge=0,le=1e8)
    estoque_fisico: Optional[float]=Field(None,ge=0,le=1e9)
    estoque_registrado: Optional[float]=Field(None,ge=0,le=1e9)

    @model_validator(mode='after')
    def coerencia(self):
        for numerador,denominador in [('horas_ausencia','horas_contratadas'),('cancelamentos','base_recorrentes'),('pedidos','leads')]:
            a,b=getattr(self,numerador),getattr(self,denominador)
            if a is not None and b is not None and a>b:
                raise ValueError(f'{numerador} não pode superar {denominador} nesta base.')
        return self


def resultado_semana(db, empresa_id, rodada):
    r=db.query(Resultado).filter_by(empresa_id=empresa_id,rodada=rodada).first()
    if not r:
        raise HTTPException(404,'Encerre esta rodada para consultar seus resultados.')
    return r


def calcular_dashboard(resultado,bases):
    op=(resultado.detalhes_simulacao or {}).get('operacao',{})
    def dividir(a,b,fator=1):
        return a/b*fator if a is not None and b is not None and b>0 else None
    def item(valor,origem='Dados informados pela equipe',unidade=''):
        return {'valor':valor,'estado':'Dados indisponíveis' if valor is None else origem,'unidade':unidade}
    total_nps=sum(bases.get(k) or 0 for k in ('promotores','neutros','detratores')) if all(bases.get(k) is not None for k in ('promotores','neutros','detratores')) else None
    painel = {'marketing':{
        'CAC':item(dividir(bases.get('marketing'),bases.get('novos_clientes')),unidade='R$'),
        'Conversão':item(dividir(bases.get('pedidos'),bases.get('leads'),100),unidade='%'),
        'CPL':item(dividir(bases.get('marketing'),bases.get('leads')),unidade='R$'),
        'CPC':item(dividir(bases.get('marketing'),bases.get('cliques')),unidade='R$'),
        'Churn':item(dividir(bases.get('cancelamentos'),bases.get('base_recorrentes'),100),unidade='%'),
        'NPS':item(dividir((bases.get('promotores') or 0)-(bases.get('detratores') or 0),total_nps,100),unidade='pontos')},
        'rh':{'Absenteísmo':item(dividir(bases.get('horas_ausencia'),bases.get('horas_contratadas'),100),unidade='%'),
              'Receita por colaborador':item(dividir(resultado.receita,resultado.funcionarios),'Valor Calculado','R$'),
              'Horas extras planejadas da equipe':item(op['horas_extras']*resultado.funcionarios if op.get('horas_extras') is not None else None,'Estimativa do Modelo','h'),
              'eNPS':item(op.get('enps'),'Estimativa do Modelo','pontos')},
        'producao':{'OEE':item(op.get('oee')*100 if op.get('oee') is not None else None,'Estimativa do Modelo','%'),
                    'Produção planejada':item(op.get('producao_planejada'),'Valor Calculado','un.'),
                    'Produção realizada':item(op.get('producao_real'),'Valor Calculado','un.'),
                    'Refugo':item(dividir(op.get('refugo'),op.get('producao_real'),100),'Valor Calculado','%')},
        'logistica':{'OTIF':item(op.get('otif')*100 if op.get('otif') is not None else None,'Estimativa do Modelo','%'),
                     'Tempo médio de separação':item(bases.get('picking_minutos'),unidade='min'),
                     'Relação físico / registrado':item(dividir(bases.get('estoque_fisico'),bases.get('estoque_registrado'),100),unidade='%')}}

    if bases.get('marketing') is None and bases.get('novos_clientes') is None and op.get('cac') is not None:
        painel['marketing']['CAC']=item(op['cac'],'Estimativa do Modelo','R$')
    if bases.get('cancelamentos') is None and bases.get('base_recorrentes') is None:
        painel['marketing']['Churn']=item(dividir(op.get('clientes_perdidos'),op.get('clientes_iniciais'),100),'Estimativa do Modelo','%')
    for area,nome,chave in [("producao","OEE","oee"),("logistica","OTIF","otif"),("rh","eNPS","enps")]:
        if chave in op and op[chave] is None:
            painel[area][nome]["estado"]="Não se aplica"
    return painel


def consultar(db,empresa_id,rodada):
    r=resultado_semana(db,empresa_id,rodada)
    obs=db.query(ObservacaoSemanal).filter_by(empresa_id=empresa_id,rodada=rodada).first()
    bases=obs.dados if obs else {}
    return {'bases':bases,'indicadores':calcular_dashboard(r,bases),
            'calendario':(r.detalhes_simulacao or {}).get('calendario'),
            'atualizado_em':obs.atualizado_em.isoformat()+'Z' if obs else None}
