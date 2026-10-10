"""Versões dos snapshots; leitura histórica nunca escreve no banco."""
from copy import deepcopy

ENGINE_VERSION = '2.0.0-deterministic-indicators'
LEGACY_ENGINE_VERSION = '1.0.0-legacy'


def versao_snapshot(snapshot):
    return (snapshot or {}).get('engine_version') or LEGACY_ENGINE_VERSION


def snapshot_para_leitura(snapshot):
    if snapshot is None:
        return None
    resultado = deepcopy(snapshot)
    resultado['engine_version'] = versao_snapshot(snapshot)
    return resultado


def inicializar_indicadores(estado):
    """Executado somente na cópia de trabalho de uma nova rodada."""
    if estado.get('engine_version') != ENGINE_VERSION:
        estado['indicadores_didaticos'] = {
            'risco_quebra': 0.0, 'performance': 1.0,
            'taxa_defeito': .02, 'rodadas_horas_extras': 0,
        }
        for maquina in estado.get('maquinas') or []:
            maquina['risco_quebra'] = 0.0
            maquina['condicao'] = 1.0
    estado['engine_version'] = ENGINE_VERSION
