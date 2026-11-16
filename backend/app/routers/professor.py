import csv
from datetime import date, time
import io
import json
import secrets
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, or_
from sqlalchemy.orm import Session

from .. import config
from .. import serializacao as ser
from ..experiencia import jornada_empresa
from ..database import get_db
from ..equipes import (
    FAIXA_EQUIPE, MAX_INTEGRANTES, MIN_INTEGRANTES, bloquear_turma, novo_convite, invalidar_aprovacoes, registrar,
    dados_equipe, decisao_atual, formacao_aberta, pendencias_equipe, pendencias_fechamento, pendencias_formacao, verificar_rodada,
)
from ..models import (
    AcessoAba, AprovacaoDecisao, ConteudoMercado, Decisao, DiagnosticoEstrategico, PesquisaAutomatica,
    Empresa, EventoOperacional, EventoRodada, MatriculaTurma, MembroEmpresa,
    ObservacaoSemanal, Papel, RegistroEquipe, RelatorioEmpresarial, Resultado,
    StatusTurma, Turma, Usuario,
)
from ..motor.eventos import opcoes_evento
from ..motor.simulacao import processar_rodada
from ..schemas import AgendaAcademicaEntrada, AlunoTesteEntrada, FecharRodadaEntrada, ParametrosTurma, ProfessorConvidadoEntrada, TurmaEntrada
from ..seguranca import exigir_professor, exigir_proprietario, gerar_hash_senha, trocar_senha
from .auth import normalizar_email

router = APIRouter(prefix="/api/professor", tags=["professor"])

_ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O e 1/I para evitar confusão


def _gerar_codigo(db: Session) -> str:
    while True:
        codigo = "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(6))
        if not db.query(Turma).filter(Turma.codigo == codigo).first():
            return codigo


def _turma_do_professor(db: Session, turma_id: int, professor: Usuario) -> Turma:
    turma = db.get(Turma, turma_id)
    if turma is None or (turma.professor_id != professor.id and professor.papel != Papel.PROPRIETARIO):
        raise HTTPException(404, "Turma não encontrada.")
    return turma


@router.get("/eventos")
def listar_eventos(_: Usuario = Depends(exigir_professor)):
    return opcoes_evento()


@router.get("/turmas")
def listar_turmas(db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    consulta = db.query(Turma)
    if professor.papel != Papel.PROPRIETARIO:
        consulta = consulta.filter(Turma.professor_id == professor.id)
    turmas = consulta.order_by(Turma.id.desc()).all()
    return [ser.turma(t) for t in turmas]


@router.get("/proprietario/professores")
def listar_professores(db: Session = Depends(get_db), _: Usuario = Depends(exigir_proprietario)):
    docentes = db.query(Usuario).filter(Usuario.papel == Papel.PROFESSOR).order_by(Usuario.nome).all()
    return [
        {
            "id": docente.id,
            "nome": docente.nome,
            "email": docente.email,
            "turmas": db.query(Turma).filter(Turma.professor_id == docente.id).count(),
        }
        for docente in docentes
    ]


@router.post("/proprietario/professores", status_code=201)
def convidar_professor(
    dados: ProfessorConvidadoEntrada,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_proprietario),
):
    email = normalizar_email(dados.email)
    dominio = email.rsplit("@", 1)[-1]
    if dominio not in config.DOMINIOS_PROFESSOR:
        dominios = " ou ".join(f"@{item}" for item in config.DOMINIOS_PROFESSOR)
        raise HTTPException(422, f"Use um e-mail docente autorizado: {dominios}.")
    if db.query(Usuario).filter(Usuario.email == email).first():
        raise HTTPException(409, "Já existe uma conta com este e-mail.")
    docente = Usuario(
        nome=dados.nome.strip(), email=email, senha_hash=gerar_hash_senha(dados.senha_provisoria), papel=Papel.PROFESSOR,
    )
    db.add(docente)
    db.commit()
    db.refresh(docente)
    return {"id": docente.id, "nome": docente.nome, "email": docente.email, "mensagem": "Conta docente criada. Compartilhe a senha provisória por um canal seguro."}


@router.post("/turmas", status_code=201)
def criar_turma(
    dados: TurmaEntrada, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)
):
    turma = Turma(professor_id=professor.id, codigo=_gerar_codigo(db), **dados.model_dump())
    if turma.modo_jogo != "LEGADO" and (turma.configuracao_simulacao or {}).get("periodicidade") == "SEMANAL":
        from datetime import datetime
        from zoneinfo import ZoneInfo
        turma.configuracao_simulacao = {**turma.configuracao_simulacao, "data_inicio_simulada": datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()}
    if (turma.configuracao_simulacao or {}).get("periodicidade") == "MENSAL_CALENDARIO" and not turma.configuracao_simulacao.get("sazonalidade_pmc"):
        from ..motor.sazonalidade_pmc import edicao_vigente
        turma.configuracao_simulacao = {**turma.configuracao_simulacao, "sazonalidade_pmc": edicao_vigente(db)}
    db.add(turma)
    db.commit()
    db.refresh(turma)
    return ser.turma(turma, completa=True)


class ConfirmacaoExclusaoTurma(BaseModel):
    """Evita que um clique acidental apague uma turma inteira."""

    confirmacao: str = Field(min_length=1, max_length=120)


@router.delete("/turmas/{turma_id}")
def excluir_turma(
    turma_id: int,
    dados: ConfirmacaoExclusaoTurma,
    db: Session = Depends(get_db),
    professor: Usuario = Depends(exigir_professor),
):
    """Remove uma turma e apenas os registros que pertencem a ela.

    A turma só pode ser excluída pelo seu professor responsável — ou pelo
    proprietário — e exige a digitação do nome, pois a operação é irreversível.
    Contas de alunos e professores nunca são removidas.
    """
    turma = _turma_do_professor(db, turma_id, professor)
    if dados.confirmacao.strip() != turma.nome:
        raise HTTPException(422, "Digite exatamente o nome da turma para confirmar a exclusão.")

    # A ordem respeita as chaves estrangeiras. Não dependemos de cascade no
    # banco, assim a operação se comporta da mesma forma em PostgreSQL e SQLite.
    empresa_ids = [empresa.id for empresa in turma.empresas]
    if empresa_ids:
        db.execute(delete(AprovacaoDecisao).where(AprovacaoDecisao.empresa_id.in_(empresa_ids)))
        db.execute(delete(AcessoAba).where(AcessoAba.empresa_id.in_(empresa_ids)))
        db.execute(delete(ObservacaoSemanal).where(ObservacaoSemanal.empresa_id.in_(empresa_ids)))
        db.execute(delete(RelatorioEmpresarial).where(RelatorioEmpresarial.empresa_id.in_(empresa_ids)))
        db.execute(delete(DiagnosticoEstrategico).where(DiagnosticoEstrategico.empresa_id.in_(empresa_ids)))
        db.execute(delete(EventoOperacional).where(EventoOperacional.empresa_id.in_(empresa_ids)))
        db.execute(delete(Resultado).where(Resultado.empresa_id.in_(empresa_ids)))
        db.execute(delete(RegistroEquipe).where(RegistroEquipe.empresa_id.in_(empresa_ids)))
        db.execute(delete(MembroEmpresa).where(MembroEmpresa.empresa_id.in_(empresa_ids)))
        db.execute(delete(Decisao).where(Decisao.empresa_id.in_(empresa_ids)))
        db.execute(delete(Empresa).where(Empresa.id.in_(empresa_ids)))

    # O segundo filtro de membros cobre também eventuais vínculos incompletos
    # de importações antigas, antes da remoção da turma.
    db.execute(delete(MembroEmpresa).where(MembroEmpresa.turma_id == turma.id))
    db.execute(delete(EventoOperacional).where(EventoOperacional.turma_id == turma.id))
    db.execute(delete(EventoRodada).where(EventoRodada.turma_id == turma.id))
    db.execute(delete(PesquisaAutomatica).where(PesquisaAutomatica.turma_id == turma.id))
    edicoes_da_turma = db.query(ConteudoMercado.id).filter(ConteudoMercado.turma_id == turma.id).subquery()
    db.execute(delete(DiagnosticoEstrategico).where(DiagnosticoEstrategico.edicao_id.in_(edicoes_da_turma)))
    db.execute(delete(ConteudoMercado).where(ConteudoMercado.turma_id == turma.id))
    db.execute(delete(MatriculaTurma).where(or_(MatriculaTurma.turma_id == turma.id, MatriculaTurma.autorizada_turma_id == turma.id)))
    nome = turma.nome
    db.execute(delete(Turma).where(Turma.id == turma.id))
    db.commit()
    return {"id": turma_id, "mensagem": f"Turma '{nome}' excluída."}


class CalendarioEntrada(BaseModel):
    data_inicio: date


@router.put("/turmas/{turma_id}/calendario")
def definir_calendario(turma_id: int, dados: CalendarioEntrada, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    """O professor escolhe o mês da rodada 1 (padrão: mês real de início)."""
    turma = _turma_do_professor(db, turma_id, professor)
    turma = bloquear_turma(db, turma.id)
    if turma.modo_jogo == "LEGADO":
        raise HTTPException(422, "O calendário mensal requer o modelo Tradicional ou Startup.")
    if (turma.configuracao_simulacao or {}).get("periodicidade") == "SEMANAL":
        raise HTTPException(422, "Esta turma usa o calendário semanal anterior, que não pode ser reposicionado.")
    if turma.rodada_atual != 1:
        raise HTTPException(422, "O mês inicial só pode ser escolhido antes do fechamento da primeira rodada.")
    if db.query(Decisao).join(Empresa).filter(Empresa.turma_id==turma.id, Decisao.rodada==turma.rodada_atual).first():
        raise HTTPException(422, "Defina o mês inicial antes de salvar decisões da rodada atual.")
    from ..calendario_automatico import configurar_mes
    configurar_mes(db, turma, dados.data_inicio)
    # Mês escolhido pelo professor: a agenda e o encerramento não o alteram.
    turma.configuracao_simulacao = {**turma.configuracao_simulacao, "calendario_automatico": False}
    db.commit()
    return ser.turma(turma, completa=True)


@router.put("/turmas/{turma_id}/agenda-academica")
def programar_agenda_academica(
    turma_id: int,
    dados: AgendaAcademicaEntrada,
    db: Session = Depends(get_db),
    professor: Usuario = Depends(exigir_professor),
):
    """Programa todas as janelas reais de decisão a partir dos encontros da disciplina."""
    turma = _turma_do_professor(db, turma_id, professor)
    turma = bloquear_turma(db, turma.id)
    if turma.status != StatusTurma.ABERTA:
        raise HTTPException(422, "A simulação já foi encerrada.")
    if db.query(Decisao).join(Empresa).filter(Empresa.turma_id == turma.id, Decisao.rodada == turma.rodada_atual).first():
        raise HTTPException(422, "Programe o calendário antes de salvar decisões da rodada atual.")
    from ..agenda_academica import programar
    programar(turma, dados)
    # O mês simulado acompanha a primeira aula de decisão. Com a formação
    # aberta, o calendário só é fixado quando o professor a encerrar.
    from ..calendario_automatico import ajustar_ao_inicio
    ajustar_ao_inicio(db, turma, agenda=True)
    db.commit()
    db.refresh(turma)
    return ser.turma(turma, completa=True)


@router.put("/turmas/{turma_id}/parametros")
def atualizar_parametros(
    turma_id: int,
    dados: ParametrosTurma,
    db: Session = Depends(get_db),
    professor: Usuario = Depends(exigir_professor),
):
    turma = _turma_do_professor(db, turma_id, professor)
    turma = bloquear_turma(db, turma.id)
    campos_concorrencia = {"concorrentes_virtuais", "nivel_concorrencia", "estrutura_mercado", "forca_concorrentes"}
    for campo in ("modo_jogo", "cenario", "configuracao_simulacao"):
        if campo in dados.model_fields_set:
            atual = getattr(turma, campo)
            novo = dados.model_dump()[campo]
            if campo == "configuracao_simulacao":
                from ..motor.avancado import config
                atual = config(turma)
                atual = {k: v for k, v in atual.items() if k not in campos_concorrencia}
                novo = {k: v for k, v in novo.items() if k not in campos_concorrencia}
            if novo != atual and (turma.empresas or turma.rodada_atual > 1):
                raise HTTPException(422, "Escolha o modo, cenário e configuração da simulação antes de criar empresas.")
    converter_equipes = "modo_equipe" in dados.model_fields_set and dados.modo_equipe and not turma.modo_equipe
    if "modo_equipe" in dados.model_fields_set and not dados.modo_equipe and turma.modo_equipe:
        if turma.rodada_atual > 1 or turma.empresas:
            raise HTTPException(422, "Uma turma com empresas não pode voltar ao modo individual.")
    if converter_equipes:
        turma.modo_equipe = True
        for empresa in turma.empresas:
            empresa.lider_id = empresa.aluno_id
            empresa.codigo_convite = empresa.codigo_convite or novo_convite()
            if not any(m.aluno_id == empresa.aluno_id for m in empresa.membros):
                db.add(MembroEmpresa(empresa_id=empresa.id, turma_id=turma.id, aluno_id=empresa.aluno_id, cargos=["CEO"]))
            versao = invalidar_aprovacoes(db, empresa)
            registrar(db, empresa, empresa.aluno, "CONVERTER_EQUIPE", versao, {"professor_id": professor.id})
    if turma.rodada_atual > 1:
        # Depois da 1ª rodada só o número total de rodadas pode mudar, para não distorcer a competição
        if dados.total_rodadas < turma.rodada_atual - 1:
            raise HTTPException(422, "O total de rodadas não pode ser menor que as rodadas já jogadas.")
        turma.total_rodadas = dados.total_rodadas
        if "configuracao_simulacao" in dados.model_fields_set:
            from ..motor.avancado import config
            configuracao = config(turma)
            configuracao.update({k: v for k, v in dados.configuracao_simulacao.model_dump().items() if k in campos_concorrencia})
            turma.configuracao_simulacao = configuracao
        if turma.rodada_atual <= turma.total_rodadas:
            turma.status = StatusTurma.ABERTA
    else:
        caixa_anterior = turma.caixa_inicial
        valores = dados.model_dump()
        for campo in ("modo_equipe", "modo_jogo", "cenario", "configuracao_simulacao"):
            if campo not in dados.model_fields_set:
                valores.pop(campo)
        for campo, valor in valores.items():
            setattr(turma, campo, valor)
        for empresa in turma.empresas:
            fator = .25 if turma.modo_jogo != "LEGADO" and turma.cenario == "CRISE" else 1
            if empresa.caixa == caixa_anterior * fator:
                empresa.caixa = turma.caixa_inicial * fator
    db.commit()
    db.refresh(turma)
    return ser.turma(turma, completa=True)


@router.get("/turmas/{turma_id}")
def detalhar_turma(
    turma_id: int, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)
):
    turma = _turma_do_professor(db, turma_id, professor)
    from ..calendario_automatico import iniciar_calendario
    iniciar_calendario(db, turma)
    enviadas = {
        d.empresa_id
        for d in db.query(Decisao).filter(
            Decisao.rodada == turma.rodada_atual,
            Decisao.automatica == 0,
            Decisao.enviada_em.is_not(None),
            Decisao.empresa_id.in_([e.id for e in turma.empresas] or [0]),
        )
    }
    empresas = []
    for e in turma.empresas:
        dados = ser.empresa(e)
        pendencias = pendencias_equipe(e, decisao_atual(db, e)) if turma.modo_equipe else []
        dados["decisao_enviada"] = not pendencias if turma.modo_equipe else e.id in enviadas
        dados["decisao_pronta"] = dados["decisao_enviada"]
        dados["equipe_pendencias"] = pendencias
        empresas.append(dados)
    return {
        "turma": ser.turma(turma, completa=True),
        "empresas": empresas,
        "ranking": ser.ranking(turma),
        "eventos": [ser.evento(ev) for ev in turma.eventos],
        "mercado": _resumo_mercado(db, turma),
    }


def _resumo_mercado(db: Session, turma: Turma):
    ids = [e.id for e in turma.empresas] or [0]
    resumo = []
    for rodada in range(1, turma.rodada_atual):
        resultados = (
            db.query(Resultado).filter(Resultado.rodada == rodada, Resultado.empresa_id.in_(ids)).all()
        )
        if not resultados:
            continue
        resumo.append(
            {
                "rodada": rodada,
                "preco_medio": sum(r.preco for r in resultados) / len(resultados),
                "unidades": sum(r.unidades_vendidas for r in resultados),
                "receita": sum(r.receita for r in resultados),
                "lucro": sum(r.lucro_liquido for r in resultados),
            }
        )
    return resumo


@router.get("/turmas/{turma_id}/empresas/{empresa_id}")
def detalhar_empresa(
    turma_id: int,
    empresa_id: int,
    db: Session = Depends(get_db),
    professor: Usuario = Depends(exigir_professor),
):
    turma = _turma_do_professor(db, turma_id, professor)
    empresa = db.get(Empresa, empresa_id)
    if empresa is None or empresa.turma_id != turma.id:
        raise HTTPException(404, "Empresa não encontrada nesta turma.")
    decisoes = {d.rodada: ser.decisao(d) for d in empresa.decisoes}
    return {
        "empresa": ser.empresa(empresa),
        "resultados": [ser.resultado(r) for r in empresa.resultados],
        "decisoes": [decisoes[r] for r in sorted(decisoes)],
        # O professor pode auditar o que já ocorreu, mas não recebe a semente
        # do sorteio nem qualquer controle para criar, editar ou antecipar eventos.
        "eventos_operacionais": [
            ser.evento_operacional(evento)
            for evento in sorted(
                empresa.eventos_operacionais,
                key=lambda evento: (evento.rodada_inicio, evento.id),
                reverse=True,
            )
        ],
        "jornada": jornada_empresa(empresa),
        "equipe": dados_equipe(empresa, decisao_atual(db, empresa)),
    }


@router.post("/turmas/{turma_id}/fechar-rodada")
def fechar_rodada(
    turma_id: int,
    background_tasks: BackgroundTasks,
    dados: FecharRodadaEntrada,
    db: Session = Depends(get_db),
    professor: Usuario = Depends(exigir_professor),
):
    turma = _turma_do_professor(db, turma_id, professor)
    # O fechamento usa a última edição oficial validada. A consulta nova às
    # fontes oficiais (até dois pedidos à IA com busca na web) rodava aqui,
    # antes do processamento, e deixava o encerramento em 40–50 s. Ela passa a
    # rodar em segundo plano, depois da resposta; se falhar, a última edição
    # confirmada continua valendo e o estado PENDENTE deixa isso explícito.
    from ..atualizacoes_oficiais import atualizar
    turma = bloquear_turma(db, turma.id)
    verificar_rodada(dados.rodada, turma, obrigatoria=turma.modo_jogo != "LEGADO")
    pendencias = pendencias_fechamento(db, turma)
    if pendencias and not dados.forcar:
        raise HTTPException(422, "Equipes pendentes: " + "; ".join(pendencias))
    try:
        evento = processar_rodada(db, turma, dados.evento, forcar=dados.forcar)
    except ValueError as erro:
        db.rollback()
        raise HTTPException(422, str(erro))
    db.refresh(turma)
    from .mercado import preparar_relatorios_automaticos
    background_tasks.add_task(preparar_relatorios_automaticos, turma.id, professor.id, evento.rodada, db.get_bind())
    background_tasks.add_task(atualizar, True)
    return {"evento": ser.evento(evento), "turma": ser.turma(turma, completa=True)}


@router.get("/turmas/{turma_id}/exportar.csv")
def exportar_csv(
    turma_id: int, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)
):
    turma = _turma_do_professor(db, turma_id, professor)
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    cabecalho = [
        "rodada", "empresa", "aluno", "email", "regime", "preco", "unidades_vendidas",
        "participacao_mercado", "receita", "impostos", "cmv", "folha", "custos_fixos",
        "marketing", "pd", "networking", "rescisoes", "royalties", "juros", "multas",
        "lucro_liquido", "caixa_final", "divida_final", "funcionarios", "fase",
        "autoeficacia", "networking_indice", "necessidade_realizacao",
        "equipe", "cargos", "versao_decisao", "aprovacoes", "participacao_individual",
    ]
    escritor.writerow(cabecalho)
    for e in turma.empresas:
        for r in e.resultados:
            decisao = next((d for d in e.decisoes if d.rodada == r.rodada), None)
            membros = e.membros if turma.modo_equipe else []
            aprovacoes = [
                {
                    "aluno": a.aluno.nome, "aluno_id": a.aluno_id, "versao": a.versao,
                    "aprovado_em": a.aprovado_em.isoformat() + "Z",
                }
                for a in (decisao.aprovacoes if decisao else [])
            ]
            participacao = [
                {
                    "aluno": registro.aluno.nome, "aluno_id": registro.aluno_id,
                    "acao": registro.acao, "versao": registro.versao,
                    "data": registro.data.isoformat() + "Z",
                }
                for registro in e.registros_equipe if registro.rodada == r.rodada
            ]
            escritor.writerow(
                [
                    r.rodada, e.nome, e.aluno.nome, e.aluno.email, r.regime.value,
                    _br(r.preco), _br(r.unidades_vendidas), _br(r.participacao_mercado),
                    _br(r.receita), _br(r.impostos), _br(r.cmv), _br(r.folha), _br(r.custos_fixos),
                    _br(r.marketing), _br(r.pd), _br(r.networking_invest), _br(r.rescisoes),
                    _br(r.royalties), _br(r.juros), _br(r.multas), _br(r.lucro_liquido),
                    _br(r.caixa_final), _br(r.divida_final), r.funcionarios, r.fase.value,
                    _br(r.autoeficacia), _br(r.networking), _br(r.necessidade_realizacao),
                    ", ".join(m.aluno.nome for m in membros),
                    json.dumps([{"aluno": m.aluno.nome, "cargos": m.cargos} for m in membros], ensure_ascii=False),
                    decisao.versao if decisao else 0,
                    json.dumps(aprovacoes, ensure_ascii=False),
                    json.dumps(participacao, ensure_ascii=False),
                ]
            )
    conteudo = "﻿" + saida.getvalue()  # BOM para o Excel reconhecer acentos
    nome_arquivo = f"semprehub_{turma.codigo}.csv"
    return StreamingResponse(
        iter([conteudo]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


def _br(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


# ---------------------------------------------------------------------------
# Contas de aluno criadas pelo professor e redefinição de senha
# ---------------------------------------------------------------------------
_ALFABETO_SENHA = "abcdefghjkmnpqrstuvwxyz23456789"


class RedefinirSenhaAlunoEntrada(BaseModel):
    nova_senha: Optional[str] = Field(None, min_length=8, max_length=128)


@router.get("/alunos-teste")
def listar_alunos_teste(db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    alunos = (
        db.query(Usuario)
        .filter(Usuario.criado_por_id == professor.id)
        .order_by(Usuario.id.desc())
        .all()
    )
    return [ser.usuario(a) for a in alunos]


@router.post("/alunos-teste", status_code=201)
def criar_aluno_teste(
    dados: AlunoTesteEntrada, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)
):
    """Cria uma conta de aluno com qualquer e-mail (inclusive inexistente), para testes e demonstrações."""
    email = normalizar_email(dados.email)
    if db.query(Usuario).filter(Usuario.email == email).first():
        raise HTTPException(409, "Já existe uma conta com este e-mail.")
    aluno = Usuario(
        nome=dados.nome.strip(),
        email=email,
        senha_hash=gerar_hash_senha(dados.senha),
        papel=Papel.ALUNO,
        criado_por_id=professor.id,
    )
    db.add(aluno)
    db.commit()
    db.refresh(aluno)
    return ser.usuario(aluno)


@router.post("/alunos/{aluno_id}/redefinir-senha")
def redefinir_senha_aluno(
    aluno_id: int,
    dados: RedefinirSenhaAlunoEntrada,
    db: Session = Depends(get_db),
    professor: Usuario = Depends(exigir_professor),
):
    """O professor redefine a senha de um aluno da sua turma ou de um aluno de teste que ele criou."""
    aluno = db.get(Usuario, aluno_id)
    if aluno is None or aluno.papel != Papel.ALUNO:
        raise HTTPException(404, "Aluno não encontrado.")
    eh_da_turma = (
        db.query(Empresa)
        .join(Turma, Empresa.turma_id == Turma.id)
        .filter(
            or_(Empresa.aluno_id == aluno.id, Empresa.membros.any(MembroEmpresa.aluno_id == aluno.id)),
            Turma.professor_id == professor.id,
        )
        .first()
        is not None
    )
    if not eh_da_turma and aluno.criado_por_id != professor.id:
        raise HTTPException(404, "Aluno não encontrado.")
    nova = dados.nova_senha or "".join(secrets.choice(_ALFABETO_SENHA) for _ in range(10))
    trocar_senha(db, aluno, nova)
    db.commit()
    return {"aluno": ser.usuario(aluno), "nova_senha": nova}


class IngressoTurmaEntrada(BaseModel):
    visivel_ingresso: bool
    formacao_encerrada: bool


@router.put("/turmas/{turma_id}/ingresso")
def configurar_ingresso(turma_id: int, dados: IngressoTurmaEntrada, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    turma = _turma_do_professor(db, turma_id, professor)
    turma = bloquear_turma(db, turma.id)
    if not dados.formacao_encerrada and (turma.rodada_atual != 1 or turma.status != StatusTurma.ABERTA):
        raise HTTPException(422, "Não é possível reabrir a formação após o início das rodadas.")
    if not dados.formacao_encerrada and turma.formacao_encerrada and turma.modo_equipe and _rodada_iniciada(db, turma):
        raise HTTPException(422, "Não é possível reabrir a formação depois que as equipes começaram a decidir.")
    turma.visivel_ingresso = dados.visivel_ingresso
    if dados.formacao_encerrada and not turma.formacao_encerrada:
        _encerrar_formacao(db, turma)
    elif not dados.formacao_encerrada and turma.formacao_encerrada:
        turma.formacao_encerrada = False
        from ..agenda_academica import aplicar_proxima_janela
        aplicar_proxima_janela(turma)
    db.commit()
    return ser.turma(turma)


def _rodada_iniciada(db: Session, turma: Turma) -> bool:
    return db.query(Decisao).join(Empresa).filter(Empresa.turma_id == turma.id, Decisao.rodada == turma.rodada_atual).first() is not None


def _encerrar_formacao(db: Session, turma: Turma) -> None:
    """Encerra a formação e inicia o jogo (regra do professor, 15/11/2026).

    Exige todos os cadastrados em equipes de 2 a 5. Com agenda acadêmica, a
    rodada 1 passa para a primeira aula seguinte ao encerramento; sem agenda,
    ela abre imediatamente.
    """
    if turma.modo_equipe:
        db.flush()
        for empresa in turma.empresas:
            db.expire(empresa, ["membros"])
        pendencias = pendencias_formacao(db, turma)
        if pendencias:
            raise HTTPException(422, "A formação não pode ser encerrada. " + " ".join(pendencias))
    turma.formacao_encerrada = True
    if turma.agenda_academica:
        from ..agenda_academica import dados_salvos, programar
        programar(turma, dados_salvos(turma.agenda_academica))
    from ..calendario_automatico import ajustar_ao_inicio
    ajustar_ao_inicio(db, turma, agenda=bool(turma.agenda_academica))


@router.get("/turmas/{turma_id}/formacao")
def formacao_turma(turma_id: int, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    from ..ingresso import sala
    turma = _turma_do_professor(db, turma_id, professor)
    dados = sala(db, turma)
    dados["inscritos"] = [{"aluno_id": m.aluno_id, "nome": m.aluno.nome, "autorizada_turma_id": m.autorizada_turma_id} for m in db.query(MatriculaTurma).filter_by(turma_id=turma.id)]
    dados["turmas_destino"] = [{"id": t.id, "nome": t.nome} for t in db.query(Turma).filter(Turma.visivel_ingresso.is_(True), Turma.formacao_encerrada.is_(False), Turma.rodada_atual == 1, Turma.status == StatusTurma.ABERTA) if t.id != turma.id]
    return dados


class AutorizarTrocaEntrada(BaseModel):
    aluno_id: int = Field(gt=0)
    destino_id: int = Field(gt=0)
    motivo: str = Field(min_length=5, max_length=1000)


@router.post("/turmas/{turma_id}/autorizar-troca")
def autorizar_troca(turma_id: int, dados: AutorizarTrocaEntrada, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    _turma_do_professor(db, turma_id, professor)
    from sqlalchemy import update
    db.execute(update(Usuario).where(Usuario.id == dados.aluno_id).values(versao_sessao=Usuario.versao_sessao), execution_options={"synchronize_session": False})
    m = db.query(MatriculaTurma).filter_by(aluno_id=dados.aluno_id).populate_existing().first()
    destino = db.get(Turma, dados.destino_id)
    if not m or m.turma_id != turma_id:
        raise HTTPException(404, "Aluno não vinculado a esta turma.")
    if not destino or destino.id == turma_id or not destino.visivel_ingresso or destino.formacao_encerrada or destino.rodada_atual != 1 or destino.status != StatusTurma.ABERTA:
        raise HTTPException(422, "Escolha uma turma de destino disponível para ingresso.")
    lider = db.query(Empresa).filter_by(turma_id=turma_id, lider_id=dados.aluno_id).first()
    if lider and lider.turma.status == StatusTurma.ABERTA:
        raise HTTPException(422, "Este aluno é líder de uma equipe ativa. Transfira a liderança e aguarde a próxima rodada antes de autorizar a troca de turma.")
    m.autorizada_turma_id = destino.id
    m.historico = [*(m.historico or []), {"acao": "AUTORIZAR_TROCA", "professor_id": professor.id, "destino": destino.id, "motivo": dados.motivo.strip(), "data": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}]
    db.commit()
    return {"mensagem": "Troca autorizada. O aluno pode selecionar a turma de destino."}


@router.post("/turmas/{turma_id}/distribuir-sem-equipe")
def distribuir_sem_equipe(turma_id: int, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    import secrets
    from ..ingresso import sala
    turma = _turma_do_professor(db, turma_id, professor)
    turma = bloquear_turma(db, turma.id)
    if not turma.modo_equipe or turma.rodada_atual != 1 or turma.status != StatusTurma.ABERTA:
        raise HTTPException(422, "A distribuição só ocorre na formação das equipes, antes de fechar a primeira rodada.")
    livres = sala(db, turma)["disponiveis"]
    incompletas = [e for e in turma.empresas if len(e.membros) < MIN_INTEGRANTES]
    if incompletas:
        nomes = ", ".join(e.nome for e in incompletas)
        raise HTTPException(422, f"Equipes com menos de {MIN_INTEGRANTES} integrantes: {nomes}. Organize essas equipes antes de distribuir.")
    candidatas = [e for e in turma.empresas if MIN_INTEGRANTES <= len(e.membros) < MAX_INTEGRANTES]
    vagas = [e for e in candidatas for _ in range(MAX_INTEGRANTES-len(e.membros))]
    if len(vagas) < len(livres):
        raise HTTPException(422, f"Há {len(livres)} alunos sem equipe e apenas {len(vagas)} vagas em equipes com pelo menos {MIN_INTEGRANTES} integrantes. Organize novas equipes antes de distribuir.")
    distribuicao = []
    for aluno in livres:
        empresa = secrets.choice(vagas)
        vagas.remove(empresa)
        db.add(MembroEmpresa(empresa_id=empresa.id, turma_id=turma.id, aluno_id=aluno["aluno_id"], cargos=[]))
        versao = invalidar_aprovacoes(db, empresa)
        registrar(db, empresa, db.get(Usuario, aluno["aluno_id"]), "DISTRIBUIR_EQUIPE", versao, {"professor_id": professor.id})
        distribuicao.append({"aluno": aluno["nome"], "empresa": empresa.nome})
    db.flush()
    _encerrar_formacao(db, turma)
    db.commit()
    return {"distribuicao": distribuicao, "mensagem": "Formação encerrada; alunos sem equipe distribuídos nas vagas disponíveis."}


class InclusaoExcepcionalEntrada(BaseModel):
    aluno_id: int = Field(gt=0)
    empresa_id: int = Field(gt=0)
    motivo: str = Field(min_length=5, max_length=1000)


@router.post("/turmas/{turma_id}/inclusao-excepcional")
def incluir_excepcionalmente(turma_id: int, dados: InclusaoExcepcionalEntrada, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    turma = _turma_do_professor(db, turma_id, professor)
    turma = bloquear_turma(db, turma.id)
    m = db.get(MatriculaTurma, dados.aluno_id)
    empresa = db.get(Empresa, dados.empresa_id)
    if not turma.modo_equipe or not m or m.turma_id != turma.id or not empresa or empresa.turma_id != turma.id:
        raise HTTPException(422, "Selecione um aluno cadastrado e uma equipe desta turma.")
    if turma.status != StatusTurma.ABERTA or len(empresa.membros) >= MAX_INTEGRANTES:
        raise HTTPException(422, "A equipe não tem vaga disponível ou a turma foi encerrada.")
    if db.query(MembroEmpresa).filter_by(turma_id=turma.id, aluno_id=m.aluno_id).first() or db.query(Empresa).filter_by(turma_id=turma.id, aluno_id=m.aluno_id).first():
        raise HTTPException(409, "Este aluno já está em uma equipe.")
    db.add(MembroEmpresa(empresa_id=empresa.id, turma_id=turma.id, aluno_id=m.aluno_id, cargos=[]))
    versao = invalidar_aprovacoes(db, empresa)
    registrar(db, empresa, m.aluno, "INCLUSAO_EXCEPCIONAL", versao, {"professor_id": professor.id, "motivo": dados.motivo.strip()})
    db.commit()
    return {"mensagem": "Inclusão excepcional registrada com justificativa."}


class ProrrogacaoEntrada(BaseModel):
    rodada: int = Field(ge=1, le=60)
    # Dia e hora no horário de Brasília; ambos vazios cancelam a extensão.
    data: Optional[date] = None
    horario: Optional[time] = None


@router.put("/turmas/{turma_id}/prorrogacao")
def estender_fechamento(turma_id: int, dados: ProrrogacaoEntrada, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    """Exceção pontual: estende o fechamento de uma rodada (ex.: aula 1 aberta por 2 ou 3 dias).

    O padrão continua automático pela agenda; as rodadas seguintes abrem na
    primeira aula depois do novo fechamento.
    """
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    from ..models import agora
    from ..agenda_academica import dados_salvos, programar
    _turma_do_professor(db, turma_id, professor)
    turma = bloquear_turma(db, turma_id)
    if turma.status != StatusTurma.ABERTA:
        raise HTTPException(409, "A turma está encerrada.")
    if not turma.agenda_academica:
        raise HTTPException(422, "Programe primeiro o calendário acadêmico. Sem calendário, use o prazo manual da rodada.")
    if not turma.rodada_atual <= dados.rodada <= turma.total_rodadas:
        raise HTTPException(422, f"Escolha uma rodada entre {turma.rodada_atual} e {turma.total_rodadas}.")
    if (dados.data is None) != (dados.horario is None):
        raise HTTPException(422, "Informe o dia e o horário do fechamento, ou deixe ambos vazios para cancelar a extensão.")
    prorrogacoes = dict(turma.agenda_academica.get("prorrogacoes") or {})
    if dados.data is None:
        prorrogacoes.pop(str(dados.rodada), None)
    else:
        limite = datetime.combine(dados.data, dados.horario, ZoneInfo("America/Sao_Paulo")).astimezone(timezone.utc).replace(tzinfo=None)
        if limite <= agora():
            raise HTTPException(422, "Escolha um fechamento que ainda não tenha passado (horário de Brasília).")
        prorrogacoes[str(dados.rodada)] = limite.isoformat() + "Z"
    turma.agenda_academica = {**turma.agenda_academica, "prorrogacoes": prorrogacoes}
    programar(turma, dados_salvos(turma.agenda_academica))
    db.commit()
    return ser.turma(turma, completa=True)


class PrazoEntrada(BaseModel):
    data: Optional[date] = None
    rodada: int = Field(ge=1)

@router.put("/turmas/{turma_id}/prazo")
def configurar_prazo(turma_id: int, dados: PrazoEntrada, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    from ..prazos import limite_brasilia
    from ..models import agora
    _turma_do_professor(db, turma_id, professor)
    turma = bloquear_turma(db, turma_id)
    verificar_rodada(dados.rodada, turma, True)
    if turma.status != StatusTurma.ABERTA:
        raise HTTPException(409, "A turma está encerrada.")
    if turma.agenda_academica:
        raise HTTPException(422, "Esta turma segue a programação acadêmica. Ajuste o calendário para alterar as datas das rodadas.")
    limite = limite_brasilia(dados.data) if dados.data else None
    if limite and limite <= agora():
        raise HTTPException(422, "Escolha uma data cujo limite ainda não tenha passado em Brasília.")
    turma.prazo_rodada = limite
    turma.prazo_numero_rodada = dados.rodada if limite else None
    db.commit()
    return ser.turma(turma, completa=True)


@router.get("/turmas/{turma_id}/acessos")
def relatorio_acessos(turma_id: int, rodada: int = 0, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    from ..models import AcessoAba, agora
    from sqlalchemy import func
    turma = _turma_do_professor(db, turma_id, professor)
    consulta = db.query(AcessoAba.aluno_id, AcessoAba.empresa_id, AcessoAba.aba,
                        func.count(AcessoAba.id), func.max(AcessoAba.criado_em)).join(Empresa, Empresa.id == AcessoAba.empresa_id).filter(Empresa.turma_id == turma.id)
    if rodada:
        consulta = consulta.filter(AcessoAba.rodada == rodada)
    grupos = consulta.group_by(AcessoAba.aluno_id, AcessoAba.empresa_id, AcessoAba.aba).all()
    alunos = {u.id: u.nome for u in db.query(Usuario).filter(Usuario.id.in_([g[0] for g in grupos] or [0])).all()}
    linhas = [{"aluno": alunos.get(a, "Aluno"), "empresa": next(e.nome for e in turma.empresas if e.id == emp),
               "aba": aba, "acessos": qtd, "ultimo_acesso": dt.isoformat()+"Z"} for a, emp, aba, qtd, dt in grupos]
    participantes = []
    for empresa in turma.empresas:
        ids = {empresa.aluno_id} | {m.aluno_id for m in empresa.membros}
        for aid in ids:
            usuario = db.get(Usuario, aid)
            participantes.append({"aluno": usuario.nome, "empresa": empresa.nome,
                                  "acessos": sum(g[3] for g in grupos if g[0] == aid and g[1] == empresa.id)})
    return {"registros": sorted(linhas, key=lambda x: x['ultimo_acesso'], reverse=True), "participantes": participantes,
            "observacao": "Registros disponíveis desde a implantação. Abrir uma aba não comprova leitura, aprendizagem ou acerto da decisão."}


@router.get('/turmas/{turma_id}/empresas/{empresa_id}/dashboard/{rodada}')
def dashboard_empresa(turma_id:int,empresa_id:int,rodada:int,db:Session=Depends(get_db),professor:Usuario=Depends(exigir_professor)):
    from ..dashboard_semanal import consultar
    _turma_do_professor(db,turma_id,professor)
    empresa=db.get(Empresa,empresa_id)
    if not empresa or empresa.turma_id!=turma_id:
        raise HTTPException(404,'Empresa não encontrada.')
    return consultar(db,empresa_id,rodada)
