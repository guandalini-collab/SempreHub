"""Calendário simulado independente do prazo real de envio. Fatores didáticos explícitos."""
from calendar import monthrange
from copy import deepcopy
from datetime import date, timedelta

VERSAO_SEMANAL = '3.1.0-auto-calendar-projected-mei'


def periodo(config, rodada):
    if config.get('periodicidade', 'MENSAL') != 'SEMANAL':
        return None
    primeira = config.get('rodada_inicio_calendario',1)
    if rodada < primeira: return None
    inicio = date.fromisoformat(config['data_inicio_simulada']) + timedelta(days=7*(rodada-primeira))
    dias = [inicio + timedelta(days=i) for i in range(7)]
    fator = sum(1/monthrange(d.year,d.month)[1] for d in dias)
    perfil = config.get('perfil_sazonal', 'NEUTRO')
    eventos = []
    def forca(d):
        valor = 1.0
        if perfil == 'NEUTRO':
            return valor
        for ano in range(d.year-1,d.year+2):
            novembro = date(ano,11,30)
            black = novembro-timedelta(days=(novembro.weekday()-4)%7)
            datas = [(date(ano,10,12),'Dia das Crianças',.40), (black,'Black Friday',.45), (date(ano,12,25),'Natal',.60)]
            for alvo,nome,pico in datas:
                distancia = (alvo-d).days
                # Varejo físico e alimentos têm perfis diferentes; serviços não herdam picos industriais.
                peso = 1 if perfil == 'VAREJO' else (.60 if nome == 'Natal' else .15) if perfil == 'ALIMENTACAO' else .10
                if 0 <= distancia <= 42:
                    valor += pico*peso*(1-distancia/49)
                    if nome not in eventos: eventos.append(nome)
                elif -7 <= distancia < 0:
                    valor -= .12*peso
                    if 'Pós-'+nome not in eventos: eventos.append('Pós-'+nome)
        return max(.5,valor)
    demanda = sum(forca(d) for d in dias)/7
    return {'periodicidade':'SEMANAL','inicio':inicio.isoformat(),'fim':dias[-1].isoformat(),
            'dias':7,'fator_mensal':fator,'semana_iso':inicio.isocalendar().week,
            'ano_iso':inicio.isocalendar().year,'ano_fiscal':dias[-1].year,
            'meses':[{'data':d.isoformat(),'peso_mensal':1/monthrange(d.year,d.month)[1]} for d in dias],
            'sazonalidade':{'estado':'Estimativa do Modelo','perfil':perfil,'eventos':eventos,
                'demanda':demanda,'insumos':1+max(0,demanda-1)*.08,'frete':1+max(0,demanda-1)*.20},
            'proximos_eventos': [{'nome':n,'data':date(a,m,d).isoformat()} for a in range(inicio.year,inicio.year+2)
                                for m,d,n in [(10,12,'Dia das Crianças'),(12,25,'Natal')]
                                if inicio <= date(a,m,d) <= inicio+timedelta(days=90)]}


def adaptar(parametros, rodada):
    p = deepcopy(parametros)
    if '_calendario' in p: return p
    cal = periodo(p.get('configuracao_simulacao') or {}, rodada)
    if not cal: return p
    from ..schemas import ConfiguracaoSimulacao
    p['configuracao_simulacao'] = ConfiguracaoSimulacao.model_validate(p.get('configuracao_simulacao') or {}).model_dump()
    for k,v in {'custos_fixos_mensais':1500,'produtividade_por_pessoa':120,'demanda_base_por_empresa':220,'das_mei_mensal':82.05,'taxa_juros_mensal':.025,'taxa_cheque_especial':.08,'crescimento_mercado_mensal':.01}.items():
        p.setdefault(k,v)
    p['_calendario'] = cal
    f = cal['fator_mensal']
    for k in ('custos_fixos_mensais','produtividade_por_pessoa','demanda_base_por_empresa','das_mei_mensal'):
        if k in p: p[k] *= f
    for k in ('taxa_juros_mensal','taxa_cheque_especial','crescimento_mercado_mensal'):
        if k in p: p[k] = (1+p[k])**f-1
    cfg=p['configuracao_simulacao']
    for k in ('custo_armazenagem','custo_nuvem_cliente'):
        if k in cfg: cfg[k]*=f
    if 'churn_base' in cfg: cfg['churn_base']=1-(1-cfg['churn_base'])**f
    for k in ('frete_rapido','frete_padrao','frete_economico','custo_frete_km'):
        if k in cfg: cfg[k]*=cal['sazonalidade']['frete']
    return p
