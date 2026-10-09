import csv
import io
import json
import secrets
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import serializacao as ser
from ..experiencia import jornada_empresa
from ..database import get_db
from ..equipes import bloquear_turma, novo_convite, invalidar_aprovacoes, registrar, dados_equipe, decisao_atual, pendencias_equipe, pendencias_fechamento, verificar_rodada
from ..models import MatriculaTurma, Decisao, Empresa, MembroEmpresa, Papel, Resultado, StatusTurma, Turma, Usuario
from ..motor.eventos import opcoes_evento
from ..motor.simulacao import processar_rodada
from ..schemas import AlunoTesteEntrada, FecharRodadaEntrada, ParametrosTurma, TurmaEntrada
from ..seguranca import exigir_professor, gerar_hash_senha, trocar_senha
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
    if turma is None or turma.professor_id != professor.id:
        raise HTTPException(404, "Turma não encontrada.")
    return turma


@router.get("/eventos")
def listar_eventos(_: Usuario = Depends(exigir_professor)):
    return opcoes_evento()


@router.get("/turmas")
def listar_turmas(db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)):
    turmas = db.query(Turma).filter(Turma.professor_id == professor.id).order_by(Turma.id.desc()).all()
    return [ser.turma(t) for t in turmas]


@router.post("/turmas", status_code=201)
def criar_turma(
    dados: TurmaEntrada, db: Session = Depends(get_db), professor: Usuario = Depends(exigir_professor)
):
    turma = Turma(professor_id=professor.id, codigo=_gerar_codigo(db), **dados.model_dump())
    db.add(turma)
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
    turma = bloquear_turma(db, turma.id)
    verificar_rodada(dados.rodada, turma, obrigatoria=turma.modo_jogo != "LEGADO")
    pendencias = pendencias_fechamento(db, turma)
    if pendencias:
        raise HTTPException(422, "Equipes pendentes: " + "; ".join(pendencias))
    try:
        evento = processar_rodada(db, turma, dados.evento)
    except ValueError as erro:
        db.rollback()
        raise HTTPException(422, str(erro))
    db.refresh(turma)
    from .mercado import preparar_relatorios_automaticos
    background_tasks.add_task(preparar_relatorios_automaticos, turma.id, professor.id, evento.rodada)
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
    turma.visivel_ingresso = dados.visivel_ingresso
    turma.formacao_encerrada = dados.formacao_encerrada
    db.commit()
    return ser.turma(turma)


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
    candidatas = [e for e in turma.empresas if 3 <= len(e.membros) < 5]
    vagas = [e for e in candidatas for _ in range(5-len(e.membros))]
    if len(vagas) < len(livres):
        raise HTTPException(422, f"Há {len(livres)} alunos sem equipe e apenas {len(vagas)} vagas em equipes com pelo menos 3 integrantes. Organize novas equipes antes de distribuir.")
    distribuicao = []
    for aluno in livres:
        empresa = secrets.choice(vagas)
        vagas.remove(empresa)
        db.add(MembroEmpresa(empresa_id=empresa.id, turma_id=turma.id, aluno_id=aluno["aluno_id"], cargos=[]))
        versao = invalidar_aprovacoes(db, empresa)
        registrar(db, empresa, db.get(Usuario, aluno["aluno_id"]), "DISTRIBUIR_EQUIPE", versao, {"professor_id": professor.id})
        distribuicao.append({"aluno": aluno["nome"], "empresa": empresa.nome})
    turma.formacao_encerrada = True
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
    if turma.status != StatusTurma.ABERTA or len(empresa.membros) >= 5:
        raise HTTPException(422, "A equipe não tem vaga disponível ou a turma foi encerrada.")
    if db.query(MembroEmpresa).filter_by(turma_id=turma.id, aluno_id=m.aluno_id).first() or db.query(Empresa).filter_by(turma_id=turma.id, aluno_id=m.aluno_id).first():
        raise HTTPException(409, "Este aluno já está em uma equipe.")
    db.add(MembroEmpresa(empresa_id=empresa.id, turma_id=turma.id, aluno_id=m.aluno_id, cargos=[]))
    versao = invalidar_aprovacoes(db, empresa)
    registrar(db, empresa, m.aluno, "INCLUSAO_EXCEPCIONAL", versao, {"professor_id": professor.id, "motivo": dados.motivo.strip()})
    db.commit()
    return {"mensagem": "Inclusão excepcional registrada com justificativa."}
