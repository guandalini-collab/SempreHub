"""Boletins oficiais automáticos, sem reescrever resultados nem executar código da IA."""
from datetime import date, timedelta
import logging
import os
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from .database import SessionLocal
from .models import BoletimOficial, ConsultaOficial, agora
from .fontes_oficiais import fonte_oficial
from .evidencias_mercado import obter_documento, normalizar
from .inteligencia_mercado import gerar_json

INTERVALO = timedelta(hours=6)
RETRY_FALHA = timedelta(minutes=15)


class ItemOficial(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    titulo: str=Field(min_length=5,max_length=180)
    tema: Literal['TRIBUTOS','ECONOMIA','MERCADO']
    resumo: str=Field(min_length=30,max_length=1600)
    instituicao: str=Field(min_length=2,max_length=160)
    url: str=Field(max_length=2000)
    publicado_em: date
    referencia: str=Field(min_length=4,max_length=100)
    vigencia_inicio: date | None
    vigencia_fim: date | None
    condicoes: str | None=Field(default=None,max_length=500)
    trecho: str=Field(min_length=30,max_length=400)

    @model_validator(mode='after')
    def validar(self):
        if not fonte_oficial(self.url):
            raise ValueError('Somente fontes oficiais são aceitas.')
        if self.vigencia_inicio and self.vigencia_fim and self.vigencia_fim<self.vigencia_inicio:
            raise ValueError('Vigência inválida.')
        return self


class Boletim(BaseModel):
    model_config=ConfigDict(extra='forbid')
    # Uma consulta pode não encontrar nenhuma publicação que passe, ao mesmo
    # tempo, pelo filtro oficial, pela data e pela prova literal. Isso é um
    # resultado válido: o sistema registra a consulta vazia, sem inventar item.
    itens: list[ItemOficial]=Field(min_length=0,max_length=8)


def habilitado():
    return bool((os.getenv('OPENAI_API_KEY') or os.getenv('SEMPREHUB_OPENAI_API_KEY')) and os.getenv('SEMPREHUB_ATUALIZACAO_OFICIAL','1')=='1')


def reservar(db, instante, forcar=False):
    if not db.get(ConsultaOficial,1):
        try:
            db.add(ConsultaOficial(id=1,estado='PENDENTE'))
            db.commit()
        except IntegrityError:
            db.rollback()
    # Reserva atômica também entre réplicas. Consultas confirmadas ficam seis
    # horas em cache; erros transitórios recebem apenas uma nova tentativa após
    # quinze minutos, sem transformar uma falha persistente em chamadas contínuas.
    criterios=[ConsultaOficial.id==1,
        or_(ConsultaOficial.ocupado_ate.is_(None),ConsultaOficial.ocupado_ate<=instante)]
    if not forcar:
        criterios.append(or_(
            ConsultaOficial.tentado_em.is_(None),
            ConsultaOficial.tentado_em<=instante-INTERVALO,
            (ConsultaOficial.estado=='PENDENTE') & (ConsultaOficial.tentado_em<=instante-RETRY_FALHA),
        ))
    r=db.execute(update(ConsultaOficial).where(*criterios)
        .values(tentado_em=instante,ocupado_ate=instante+timedelta(minutes=15),estado='CONSULTANDO',erro=None))
    db.commit()
    return r.rowcount==1


def validar_boletim(dados, fontes, hoje):
    b=Boletim.model_validate(dados)
    docs={}
    for item in b.itens:
        if item.url not in fontes or item.publicado_em>hoje:
            raise ValueError('Data ou fonte não confirmada na pesquisa.')
        if item.url not in docs:
            docs[item.url]=obter_documento(item.url,somente_oficial=True)
        if normalizar(item.trecho) not in docs[item.url].texto:
            raise ValueError('Trecho não localizado no documento oficial.')
    return b.model_dump(mode='json')


def validar_itens_confirmados(dados, fontes, hoje):
    """Mantém apenas itens individualmente comprovados.

    Uma resposta de pesquisa pode reunir documentos bons e um link que tenha
    mudado, seja PDF ou não contenha o trecho literal solicitado. Esse único
    item não pode derrubar todo o boletim. O conteúdo descartado nunca é
    exibido nem aplicado; se nada for verificável, a chamada seguinte pesquisa
    novamente com uma instrução mais restrita.
    """
    brutos = dados.get('itens', []) if isinstance(dados, dict) else []
    if not isinstance(brutos, list):
        return {'itens': []}
    confirmados=[]
    for bruto in brutos[:8]:
        try:
            confirmado=validar_boletim({'itens':[bruto]},fontes,hoje)
        except (ValueError, ValidationError, OSError):
            continue
        confirmados.extend(confirmado['itens'])
    return {'itens':confirmados}


def prompt_atualizacao(tentativa):
    instrucao=('Pesquise exclusivamente documentos originais de IBGE, Ipea, Banco Central, Receita Federal, '
        'CGSN, Diário Oficial, Planalto, Senado, ministérios e institutos de pesquisa autorizados. '
        'Prepare de um a oito atualizações nacionais relevantes a um simulador educacional de empresas brasileiras: '
        'tributos, inflação, juros, atividade, mercado e trabalho. Use a publicação mais recente disponível; '
        'indique a competência e a data original. Norma publicada não equivale a efeitos imediatos: '
        'registre início/fim da produção de efeitos e TODAS as condições de aplicação; proposta legislativa '
        'deve ser identificada como proposta, nunca imposto vigente. Não preveja fatos futuros. '
        'Cada item exige trecho literal de 30 a 400 caracteres presente na fonte. '
        'Use somente uma página HTML oficial pública, acessível sem login e que contenha o trecho literalmente; '
        'não use PDF, página de busca, página inicial, arquivos baixáveis ou URL redirecionada. '
        'Não invente cotações unitárias de produtos ausentes de pesquisa oficial. '
        'A notícia não autoriza recalcular demonstrativos nem alterar parâmetros de uma turma em andamento.')
    if tentativa:
        instrucao+=' A tentativa anterior trouxe fonte sem prova literal verificável. Pesquise novamente em páginas HTML oficiais diferentes e inclua somente itens cuja URL e trecho sejam verificáveis.'
    return instrucao


def atualizar(forcar=False):
    """Consulta fontes oficiais.

    A rotina periódica respeita o cache. Antes de abrir uma nova rodada,
    ``forcar=True`` garante uma tentativa nova, sem reutilizar uma consulta
    antiga. A reserva atômica continua impedindo duas chamadas simultâneas.
    """
    if not habilitado():
        return False
    with SessionLocal() as db:
        instante=agora()
        if not reservar(db,instante,forcar=forcar):
            return False
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime
        hoje=datetime.now(ZoneInfo('America/Sao_Paulo')).date()
        validado=None
        for tentativa in range(2):
            dados,fontes=gerar_json(prompt_atualizacao(tentativa),{'data_consulta':hoje.isoformat(),'pais':'Brasil'},True,Boletim.model_json_schema())
            candidato=validar_itens_confirmados(dados,fontes,hoje)
            if candidato['itens']:
                validado=candidato
                break
        if not validado:
            raise ValueError('Nenhum documento oficial pôde ser comprovado.')
        with SessionLocal() as db:
            db.add(BoletimOficial(dados=validado,consultado_em=agora()))
            c=db.get(ConsultaOficial,1);c.estado='CONSULTADO';c.ocupado_ate=None;c.erro=None
            db.commit()
        return True
    except Exception as erro:
        # Nunca gravar corpo da API, credenciais ou dados pessoais no log.
        motivo='Não foi possível confirmar a atualização em fontes oficiais. Última edição preservada.'
        if isinstance(erro,HTTPException) and isinstance(erro.detail,str) and erro.detail.startswith(('A integração de pesquisa','A pesquisa não respondeu','A pesquisa excedeu','A busca não encontrou','A pesquisa retornou fonte não oficial')):
            motivo=erro.detail[:500]
        logging.getLogger(__name__).warning('Consulta oficial pendente (%s).',type(erro).__name__)
        with SessionLocal() as db:
            c=db.get(ConsultaOficial,1);c.estado='PENDENTE';c.ocupado_ate=None
            c.erro=motivo
            db.commit()
        return False


def consultar(db):
    b=db.query(BoletimOficial).order_by(BoletimOficial.id.desc()).first()
    c=db.get(ConsultaOficial,1)
    return {'habilitado':habilitado(),'estado':c.estado if c else 'PENDENTE',
            'erro':c.erro if c else None,'id':b.id if b else None,
            'consultado_em':b.consultado_em.isoformat()+'Z' if b else None,
            'consulta_vencida':not b or agora()-b.consultado_em>INTERVALO,
            'intervalo_horas':6,'itens':b.dados['itens'] if b else [],
            'escopo':'Boletim oficial. Aplicações tributárias usam regras versionadas do motor; normas com condições ou sem suporte são sinalizadas, não executadas pela IA.'}
