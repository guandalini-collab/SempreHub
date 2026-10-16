"""Indicadores de análise: bases manuais nunca alteram decisões, notas ou contabilidade."""
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional
from math import isfinite
from .models import Resultado, ObservacaoSemanal
from fastapi import HTTPException


# Direções explícitas. Metas são comparações escolhidas pela equipe, sem nota automática.
DIRECOES = {
 'marketing': {'CAC':'MENOR','Conversão':'MAIOR','CPL':'MENOR','CPC':'MENOR','Churn':'MENOR','NPS':'MAIOR'},
 'rh': {'Absenteísmo':'MENOR','Receita por colaborador':'MAIOR','Horas extras planejadas da equipe':'MENOR','Horas extras realizadas':'MENOR','Turnover por desligamentos':'MENOR','eNPS':'MAIOR'},
 'producao': {'OEE':'MAIOR','Refugo':'MENOR','Aderência ao plano':'MAIOR','Tempo médio de ciclo':'MENOR'},
 'logistica': {'OTIF':'MAIOR','Tempo médio de separação':'MENOR','Custo logístico por pedido':'MENOR','Custos registrados por pedido':'MENOR','Acuracidade por itens auditados':'MAIOR'}
}


class MetaSemanal(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    alvo: float=Field(ge=-100,le=1e12)
    alerta: float=Field(ge=-100,le=1e12)


class BasesSemanais(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    metas: dict[str,MetaSemanal]=Field(default_factory=dict,max_length=30)
    anuncios: Optional[float]=Field(None,ge=0,le=1e9)
    horas_extras_realizadas: Optional[float]=Field(None,ge=0,le=1e8)
    desligamentos: Optional[int]=Field(None,ge=0,le=100000000)
    colaboradores_inicio: Optional[int]=Field(None,ge=0,le=100000000)
    ciclo_minutos: Optional[float]=Field(None,ge=0,le=1e8)
    ciclos_concluidos: Optional[int]=Field(None,ge=0,le=100000000)
    custo_logistico: Optional[float]=Field(None,ge=0,le=1e9)
    pedidos_expedidos: Optional[int]=Field(None,ge=0,le=100000000)
    itens_auditados: Optional[int]=Field(None,ge=0,le=100000000)
    itens_conformes: Optional[int]=Field(None,ge=0,le=100000000)
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
        for numerador,denominador in [('horas_ausencia','horas_contratadas'),('cancelamentos','base_recorrentes'),('pedidos','leads'),('itens_conformes','itens_auditados')]:
            a,b=getattr(self,numerador),getattr(self,denominador)
            if a is not None and b is not None and a>b:
                raise ValueError(f'{numerador} não pode superar {denominador} nesta base.')
        for chave,meta in self.metas.items():
            area,sep,nome=chave.partition('.')
            direcao=DIRECOES.get(area,{}).get(nome) if sep else None
            if direcao is None:
                raise ValueError('Indicador inválido para meta.')
            if nome not in {'NPS','eNPS'} and min(meta.alvo,meta.alerta)<0:
                raise ValueError('Esta meta não aceita valores negativos.')
            if nome in {'NPS','eNPS'} and max(meta.alvo,meta.alerta)>100:
                raise ValueError('NPS e eNPS usam pontos de -100 a 100.')
            if nome in {'Conversão','Churn','Absenteísmo','OEE','Refugo','OTIF','Acuracidade por itens auditados'} and max(meta.alvo,meta.alerta)>100:
                raise ValueError('Percentual fora da escala de 0 a 100.')
            if (direcao=='MAIOR' and meta.alerta>meta.alvo) or (direcao=='MENOR' and meta.alerta<meta.alvo):
                raise ValueError('O limite de alerta deve ser menos exigente que a meta.')
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
    inicio=op.get('funcionarios_inicio')
    saidas=op.get('desligamentos_efetivos')
    dre=(resultado.detalhes_simulacao or {}).get('dre',{})
    custo_registrado=(dre['frete']+dre['armazenagem']) if dre.get('frete') is not None and dre.get('armazenagem') is not None else None
    total_nps=sum(bases.get(k) or 0 for k in ('promotores','neutros','detratores')) if all(bases.get(k) is not None for k in ('promotores','neutros','detratores')) else None
    painel = {'marketing':{
        'CAC':item(dividir(bases.get('marketing'),bases.get('novos_clientes')),unidade='R$'),
        'Conversão':item(dividir(bases.get('pedidos'),bases.get('leads'),100),unidade='%'),
        'CPL':item(dividir(bases.get('anuncios'),bases.get('leads')),unidade='R$'),
        'CPC':item(dividir(bases.get('anuncios'),bases.get('cliques')),unidade='R$'),
        'Churn':item(dividir(bases.get('cancelamentos'),bases.get('base_recorrentes'),100),unidade='%'),
        'NPS':item(dividir((bases.get('promotores') or 0)-(bases.get('detratores') or 0),total_nps,100),unidade='pontos')},
        'rh':{'Horas extras realizadas':item(bases.get('horas_extras_realizadas'),unidade='h'),
              'Turnover por desligamentos':item(dividir(bases.get('desligamentos'),bases.get('colaboradores_inicio'),100) if 'desligamentos' in bases or 'colaboradores_inicio' in bases else dividir(saidas,inicio,100),'Dados informados pela equipe' if 'desligamentos' in bases or 'colaboradores_inicio' in bases else 'Valor Calculado','%'),
              'Absenteísmo':item(dividir(bases.get('horas_ausencia'),bases.get('horas_contratadas'),100),unidade='%'),
              'Receita por colaborador':item(dividir(resultado.receita,resultado.funcionarios),'Valor Calculado','R$'),
              'Horas extras planejadas da equipe':item(op['horas_extras']*resultado.funcionarios if op.get('horas_extras') is not None else None,'Estimativa do Modelo','h'),
              'eNPS':item(op.get('enps'),'Estimativa do Modelo','pontos')},
        'producao':{'Aderência ao plano':item(dividir(op.get('producao_real'),op.get('producao_planejada'),100),'Valor Calculado','%'),
                    'Tempo médio de ciclo':item(dividir(bases.get('ciclo_minutos'),bases.get('ciclos_concluidos')),unidade='min/ciclo'),
                    'OEE':item(op.get('oee')*100 if op.get('oee') is not None else None,'Estimativa do Modelo','%'),
                    'Produção planejada':item(op.get('producao_planejada'),'Valor Calculado','un.'),
                    'Produção realizada':item(op.get('producao_real'),'Valor Calculado','un.'),
                    'Refugo':item(dividir(op.get('refugo'),op.get('producao_real'),100),'Valor Calculado','%')},
        'logistica':{'Custo logístico por pedido':item(dividir(bases.get('custo_logistico'),bases.get('pedidos_expedidos')),unidade='R$'),
                     'Custos registrados por pedido':item(dividir(custo_registrado,op.get('pedidos_despachados')),'Valor Calculado · frete e armazenagem','R$'),
                     'Acuracidade por itens auditados':item(dividir(bases.get('itens_conformes'),bases.get('itens_auditados'),100),unidade='%'),
                     'OTIF':item(op.get('otif')*100 if op.get('otif') is not None else None,'Estimativa do Modelo','%'),
                     'Tempo médio de separação':item(bases.get('picking_minutos'),unidade='min'),
                     'Relação físico / registrado':item(dividir(bases.get('estoque_fisico'),bases.get('estoque_registrado'),100),unidade='%')}}

    if bases.get('marketing') is None and bases.get('novos_clientes') is None and op.get('cac') is not None:
        painel['marketing']['CAC']=item(op['cac'],'Estimativa do Modelo','R$')
    if bases.get('cancelamentos') is None and bases.get('base_recorrentes') is None:
        painel['marketing']['Churn']=item(dividir(op.get('clientes_perdidos'),op.get('clientes_iniciais'),100),'Estimativa do Modelo','%')
    for area,nome,chave in [("producao","OEE","oee"),("logistica","OTIF","otif"),("rh","eNPS","enps")]:
        if chave in op and op[chave] is None:
            painel[area][nome]["estado"]="Não se aplica"
    for area,indicadores in painel.items():
        for nome,indicador in indicadores.items():
            chave=f'{area}.{nome}'
            meta=bases.get('metas',{}).get(chave)
            direcao=DIRECOES.get(area,{}).get(nome)
            if not meta or not direcao:
                continue
            valor=indicador['valor']
            if valor is None or not isfinite(valor):
                status='Sem dados'
            elif (valor>=meta['alvo'] if direcao=='MAIOR' else valor<=meta['alvo']):
                status='Dentro da meta'
            elif (valor>=meta['alerta'] if direcao=='MAIOR' else valor<=meta['alerta']):
                status='Em alerta'
            else:
                status='Fora da meta'
            indicador['meta']={**meta,'direcao':direcao,'status':status}
    return painel


def consultar(db,empresa_id,rodada):
    r=resultado_semana(db,empresa_id,rodada)
    obs=db.query(ObservacaoSemanal).filter_by(empresa_id=empresa_id,rodada=rodada).first()
    bases=obs.dados if obs else {}
    return {'bases':{k:v for k,v in bases.items() if k!='metas'},'metas':bases.get('metas',{}),'direcoes':DIRECOES,'indicadores':calcular_dashboard(r,bases),
            'calendario':(r.detalhes_simulacao or {}).get('calendario'),
            'atualizado_em':obs.atualizado_em.isoformat()+'Z' if obs else None}
