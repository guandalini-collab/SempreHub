"""Pesquisa automática de mercado antes da abertura de cada rodada.

Turma com calendário acadêmico: a pesquisa da rodada começa 2 horas antes da
abertura; se falhar, há nova tentativa a cada 30 minutos (no máximo 3), e
nenhuma começa depois de 30 minutos antes da abertura, para que a edição
fique pronta com pelo menos 20 minutos de antecedência. O professor pode
revisá-la; na abertura, ela é publicada automaticamente.

Turma sem calendário: a pesquisa roda logo após o fechamento da rodada
anterior (até 3 tentativas, a cada 10 minutos) e é publicada quando fica
pronta, pois a rodada já está aberta.

Só é publicada automaticamente a edição criada por esta rotina; edições
preparadas pelo professor nunca são publicadas sem ele.
"""
import logging
from datetime import datetime, timedelta

from fastapi import HTTPException

from .models import ConteudoMercado, EventoRodada, PesquisaAutomatica, StatusTurma, Turma, agora

_log = logging.getLogger("uvicorn.error")

ANTECEDENCIA = timedelta(hours=2)
ULTIMO_INICIO = timedelta(minutes=30)
INTERVALO_COM_AGENDA = timedelta(minutes=30)
INTERVALO_SEM_AGENDA = timedelta(minutes=10)
JANELA_SEM_AGENDA = timedelta(hours=6)
TEMPO_MAXIMO = timedelta(minutes=15)
MAX_TENTATIVAS = 3


def _ia_configurada():
    import os
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("SEMPREHUB_OPENAI_API_KEY"))


def _aberturas(turma):
    """Abertura (UTC, sem fuso) de cada rodada da agenda acadêmica."""
    resultado = {}
    for item in (turma.agenda_academica or {}).get("rodadas", []):
        try:
            resultado[int(item["rodada"])] = datetime.fromisoformat(str(item["abre_em"]).replace("Z", "+00:00")).replace(tzinfo=None)
        except (KeyError, TypeError, ValueError):
            continue
    return resultado


def alvo(db, turma, instante):
    """(rodada, com_agenda) que deve ser pesquisada agora, ou None."""
    if turma.status != StatusTurma.ABERTA:
        return None
    if turma.agenda_academica:
        aberturas = _aberturas(turma)
        for rodada in (turma.rodada_atual, turma.rodada_atual + 1):
            abertura = aberturas.get(rodada)
            if rodada > turma.total_rodadas or abertura is None or abertura <= instante:
                continue
            if abertura - ANTECEDENCIA <= instante <= abertura - ULTIMO_INICIO:
                return rodada, True
        return None
    if turma.rodada_atual < 2:
        return None
    fechamento = db.query(EventoRodada).filter_by(turma_id=turma.id, rodada=turma.rodada_atual - 1).first()
    if not fechamento or not fechamento.criado_em or instante - fechamento.criado_em > JANELA_SEM_AGENDA:
        return None
    return turma.rodada_atual, False


def proxima_execucao(turma, instante=None):
    """Horário previsto da próxima pesquisa automática (só com agenda)."""
    instante = instante or agora()
    if not turma.agenda_academica or turma.status != StatusTurma.ABERTA:
        return None
    aberturas = _aberturas(turma)
    for rodada in (turma.rodada_atual, turma.rodada_atual + 1):
        abertura = aberturas.get(rodada)
        if abertura and rodada <= turma.total_rodadas and abertura > instante:
            return {"rodada": rodada, "inicio": abertura - ANTECEDENCIA, "abertura": abertura}
    return None


def _setor_da_turma(db, turma):
    ultima = (db.query(ConteudoMercado)
              .filter(ConteudoMercado.turma_id == turma.id, ConteudoMercado.publicado.is_(True))
              .order_by(ConteudoMercado.rodada.desc(), ConteudoMercado.id.desc()).first())
    setor = (turma.configuracao_simulacao or {}).get("setor_mercado") or (ultima.dados.get("setor") if ultima else None)
    comercio = (ultima.dados.get("comercio") if ultima else None) or "B2C"
    return setor, comercio


def _registrar(db, turma_id, rodada, situacao, mensagem, instante):
    db.add(PesquisaAutomatica(turma_id=turma_id, rodada=rodada, situacao=situacao, tentativas=0,
                              mensagem=mensagem[:2000], atualizado_em=instante))
    db.commit()


def pesquisar_se_preciso(db, turma_id, instante):
    from .routers.mercado import SETORES, Pesquisa, executar_pesquisa
    turma = db.get(Turma, turma_id)
    if not turma:
        return
    destino = alvo(db, turma, instante)
    if not destino:
        return
    rodada, com_agenda = destino
    registro = db.query(PesquisaAutomatica).filter_by(turma_id=turma_id, rodada=rodada).first()
    if registro is None:
        if db.query(ConteudoMercado).filter_by(turma_id=turma_id, rodada=rodada).first():
            _registrar(db, turma_id, rodada, "IGNORADA", "O professor já preparou uma edição para esta rodada; a pesquisa automática não foi feita.", instante)
            return
        setor, comercio = _setor_da_turma(db, turma)
        if setor not in SETORES:
            _registrar(db, turma_id, rodada, "IGNORADA", "A turma ainda não tem setor definido. Faça e publique a primeira pesquisa manualmente; as seguintes serão automáticas.", instante)
            return
        registro = PesquisaAutomatica(turma_id=turma_id, rodada=rodada, situacao="FALHOU", tentativas=0, atualizado_em=instante)
        db.add(registro)
        db.commit()
    if registro.situacao == "EM_ANDAMENTO" and instante - registro.atualizado_em > TEMPO_MAXIMO:
        # Tentativa interrompida (por exemplo, reinício do servidor).
        registro.situacao = "FALHOU"
        registro.mensagem = "A tentativa anterior foi interrompida antes de terminar."
        registro.proxima_tentativa = instante
        db.commit()
    if registro.situacao != "FALHOU" or registro.tentativas >= MAX_TENTATIVAS:
        return
    if registro.proxima_tentativa and instante < registro.proxima_tentativa:
        return
    setor, comercio = _setor_da_turma(db, turma)
    registro.situacao = "EM_ANDAMENTO"
    registro.tentativas += 1
    registro.mensagem = None
    registro.atualizado_em = instante
    db.commit()
    try:
        conteudo = executar_pesquisa(db, turma, Pesquisa(setor=setor, comercio=comercio), rodada, exigir_rodada_atual=False)
    except Exception as erro:
        db.rollback()
        motivo = erro.detail if isinstance(erro, HTTPException) else "Erro interno durante a pesquisa."
        if not isinstance(erro, HTTPException):
            _log.exception("Pesquisa automática da turma %s, rodada %s, falhou.", turma_id, rodada)
        registro = db.query(PesquisaAutomatica).filter_by(turma_id=turma_id, rodada=rodada).one()
        registro.situacao = "FALHOU"
        registro.mensagem = str(motivo)[:2000]
        registro.atualizado_em = agora()
        # O intervalo conta a partir do início da tentativa, para que as três
        # caibam na janela (2 h antes; última até 30 min antes da abertura).
        registro.proxima_tentativa = (instante + (INTERVALO_COM_AGENDA if com_agenda else INTERVALO_SEM_AGENDA)
                                      if registro.tentativas < MAX_TENTATIVAS else None)
        db.commit()
        return
    registro.situacao = "PRONTA"
    registro.conteudo_id = conteudo.id
    registro.mensagem = ("Edição pronta para revisão; será publicada automaticamente na abertura da rodada."
                         if com_agenda else "Edição pronta; publicada automaticamente porque a rodada já está aberta.")
    registro.atualizado_em = agora()
    registro.proxima_tentativa = None
    db.commit()


def publicar_prontas(db, turma_id, instante):
    from .equipes import bloquear_turma
    from .routers.mercado import publicar_conteudo
    turma = db.get(Turma, turma_id)
    if not turma:
        return
    for registro in db.query(PesquisaAutomatica).filter_by(turma_id=turma_id, situacao="PRONTA").all():
        if registro.rodada > turma.rodada_atual or turma.status != StatusTurma.ABERTA:
            continue
        if registro.rodada < turma.rodada_atual:
            registro.situacao, registro.mensagem = "IGNORADA", "A rodada avançou antes da publicação; a edição ficou guardada sem publicar."
            db.commit()
            continue
        if turma.abertura_rodada and instante < turma.abertura_rodada:
            continue
        if db.query(ConteudoMercado).filter_by(turma_id=turma_id, rodada=registro.rodada, publicado=True).first():
            registro.situacao, registro.mensagem = "IGNORADA", "O professor publicou outra edição nesta rodada; a automática não foi publicada."
            db.commit()
            continue
        conteudo = db.get(ConteudoMercado, registro.conteudo_id)
        if not conteudo:
            registro.situacao, registro.mensagem = "IGNORADA", "A edição automática não foi encontrada."
            db.commit()
            continue
        turma = bloquear_turma(db, turma_id)
        try:
            publicar_conteudo(db, turma, conteudo, descartar=True)
            registro.situacao = "PUBLICADA"
            registro.mensagem = "Edição publicada automaticamente na abertura da rodada."
            registro.atualizado_em = agora()
            db.commit()
        except HTTPException as erro:
            db.rollback()
            registro = db.get(PesquisaAutomatica, registro.id)
            registro.situacao = "IGNORADA"
            registro.mensagem = f"A publicação automática foi recusada: {erro.detail}"[:2000]
            registro.atualizado_em = agora()
            db.commit()


def executar_ciclo(instante=None, fabrica=None):
    """Verificação periódica (a cada minuto) de todas as turmas abertas."""
    if not _ia_configurada():
        return
    if fabrica is None:
        from .database import SessionLocal as fabrica
    instante = instante or agora()
    with fabrica() as db:
        ids = [t.id for t in db.query(Turma).filter(Turma.status == StatusTurma.ABERTA).all()]
    for turma_id in ids:
        try:
            with fabrica() as db:
                publicar_prontas(db, turma_id, instante)
                pesquisar_se_preciso(db, turma_id, instante)
                # Sem agenda, a edição recém-pesquisada já pode ser publicada.
                publicar_prontas(db, turma_id, instante)
        except Exception:
            _log.exception("Pesquisa automática pendente da turma %s; nova verificação no próximo ciclo.", turma_id)
