"""Conversão pontual autorizada de uma turma de teste; não libera alterações gerais."""
import json
from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import text

from .database import SessionLocal
from .models import Turma
from .motor.avancado import colunas, estado_inicial
from .schemas import DecisaoSimulacao


def converter(db):
    turma = db.query(Turma).filter(Turma.id == 1).with_for_update().one()
    if turma.nome != "Turma Teste" or turma.codigo != "GS9VFD":
        raise ValueError("Identificação da turma de teste não corresponde; nenhuma alteração aplicada.")
    if turma.modo_jogo == "TRADICIONAL":
        return "Turma de teste já está em Empresa tradicional; nenhuma alteração repetida."
    if turma.modo_jogo != "LEGADO" or turma.rodada_atual != 2:
        raise ValueError("Estado inesperado da turma; nenhuma alteração aplicada.")
    empresas = sorted(turma.empresas, key=lambda e: e.id)
    if not empresas:
        raise ValueError("A turma de teste não tem empresas.")
    snapshot = {"turma": colunas(turma), "empresas": [colunas(e) for e in empresas],
                "decisoes": [colunas(d) for e in empresas for d in e.decisoes]}
    backup = json.dumps(snapshot, default=lambda v: v.isoformat(), ensure_ascii=False)
    db.execute(text("CREATE TABLE IF NOT EXISTS semprehub_manutencao_backup (chave VARCHAR(120) PRIMARY KEY, dados TEXT NOT NULL, criado_em VARCHAR(40) NOT NULL)"))
    chave = "turma-1-GS9VFD-legado-tradicional-2026-10"
    db.execute(text("INSERT INTO semprehub_manutencao_backup (chave, dados, criado_em) VALUES (:chave, :dados, :data)"),
               {"chave": chave, "dados": backup, "data": datetime.now(timezone.utc).isoformat()})
    turma.modo_jogo = "TRADICIONAL"
    for empresa in empresas:
        empresa.estado_simulacao = deepcopy(estado_inicial(turma))
        for decisao in empresa.decisoes:
            if decisao.rodada == turma.rodada_atual:
                decisao.simulacao = DecisaoSimulacao().model_dump()
                decisao.versao += 1
                decisao.enviada_em = None
                decisao.automatica = 0
    db.flush()
    return f"Turma 1 convertida para Empresa tradicional na rodada 2; {len(empresas)} empresa(s). Histórico e saldos preservados; decisão atual reaberta. Backup registrado."


def main():
    with SessionLocal.begin() as db:
        mensagem = converter(db)
    print(mensagem)


if __name__ == "__main__":
    main()
