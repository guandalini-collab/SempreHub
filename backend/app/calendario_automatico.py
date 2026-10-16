"""Inicialização automática, com preservação da rodada que já possui decisões."""
from datetime import datetime
from zoneinfo import ZoneInfo
from copy import deepcopy
from math import ceil
from .models import Decisao, Empresa


def iniciar_calendario(db, turma):
    cfg = dict(turma.configuracao_simulacao or {})
    if cfg.get('calendario_automatico') is False or turma.modo_jogo == 'LEGADO' or cfg.get('periodicidade') == 'SEMANAL' or turma.status.value != 'ABERTA':
        return False
    turma = db.query(type(turma)).filter_by(id=turma.id).with_for_update().populate_existing().one()
    cfg = dict(turma.configuracao_simulacao or {})
    if cfg.get('periodicidade') == 'SEMANAL':
        return False
    if db.query(Decisao).join(Empresa).filter(Empresa.turma_id == turma.id, Decisao.rodada == turma.rodada_atual).first():
        return False
    cfg.update(periodicidade='SEMANAL', data_inicio_simulada=datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat(),
               rodada_inicio_calendario=turma.rodada_atual, calendario_automatico=True, cenario_mei_plp186=True,
               perfil_sazonal=cfg.get('perfil_sazonal', 'NEUTRO'))
    for empresa in turma.empresas:
        estado = deepcopy(empresa.estado_simulacao or {})
        def converter(r):
            return turma.rodada_atual + ceil(max(0, r-turma.rodada_atual)*30/7)
        for chave in ('receber', 'pagar'):
            for titulo in estado.get(chave, []):
                titulo['vencimento'] = converter(titulo['vencimento'])
        if estado.get('vencimento_divida') is not None:
            estado['vencimento_divida'] = converter(estado['vencimento_divida'])
        for maquina in estado.get('maquinas', []):
            maquina['ativacao'] = converter(maquina['ativacao'])
        empresa.estado_simulacao = estado
    turma.configuracao_simulacao = cfg
    db.commit()
    return True
