"""Hipótese didática explícita: tarifa base + taxa por distância média ponderada."""
from math import hypot, fsum


def estimar_frete(simulacao, configuracao):
    op = simulacao or {}
    cfg = configuracao or {}
    modal = op.get('modal', 'PADRAO')
    base = cfg.get({'RAPIDO': 'frete_rapido', 'PADRAO': 'frete_padrao', 'ECONOMICO': 'frete_economico'}[modal], {'RAPIDO': 15, 'PADRAO': 10, 'ECONOMICO': 5}[modal])
    estudo = op.get('centro_gravidade') or {}
    pontos = estudo.get('pontos') or []
    volume = fsum(p['volume'] for p in pontos)
    taxa = cfg.get('custo_frete_km', 0.1)
    distancia = 0.0
    aplicada = volume > 0 and estudo.get('local_x') is not None and estudo.get('local_y') is not None
    if aplicada:
        distancia = fsum(hypot(p['x'] - estudo['local_x'], p['y'] - estudo['local_y']) * p['volume'] for p in pontos) / volume
    adicional = round(distancia * taxa, 2)
    return {'localizacao_aplicada': aplicada, 'distancia_media_km': distancia, 'frete_base_unitario': base,
            'taxa_frete_km': taxa, 'adicional_localizacao_unitario': adicional,
            'frete_unitario': round(base + adicional, 2)}
