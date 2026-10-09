from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import serializacao as ser
from ..experiencia import jornada_empresa
from ..database import get_db
from ..equipes import (
    bloquear_turma, dados_equipe, decisao_atual, invalidar_aprovacoes,
    novo_convite, pendencias_equipe, registrar, snapshot_decisao, verificar_rodada, verificar_versao,
)
from ..models import MatriculaTurma, AprovacaoDecisao, Decisao, Empresa, MembroEmpresa, Resultado, StatusTurma, Turma, Usuario, agora
from ..motor.simulacao import perfil_inicial, prever_decisao
from ..schemas import AprovarDecisaoEntrada, DecisaoEntrada, EntrarEquipeEntrada, EntrarTurmaEntrada, EquipeEntrada
from ..seguranca import exigir_aluno
from ..ingresso import matricular, sala
from ..equipes import exigir_lider, pendencias_envio, registrar_envio
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/aluno", tags=["aluno"])


def _empresa_do_aluno(db: Session, empresa_id: int, aluno: Usuario) -> Empresa:
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise HTTPException(404, "Empresa não encontrada.")
    matricula = db.get(MatriculaTurma, aluno.id)
    if matricula and matricula.turma_id != empresa.turma_id:
        raise HTTPException(403, "Esta empresa pertence a outra turma. Procure o professor para autorizar a troca.")
    if empresa.aluno_id != aluno.id:
        membro = db.query(MembroEmpresa).filter(
            MembroEmpresa.empresa_id == empresa.id, MembroEmpresa.aluno_id == aluno.id,
        ).first() if empresa.turma.modo_equipe else None
        if membro is None:
            raise HTTPException(404, "Empresa não encontrada.")
    return empresa


def _empresa_para_alterar(db: Session, empresa_id: int, aluno: Usuario) -> Empresa:
    empresa = _empresa_do_aluno(db, empresa_id, aluno)
    bloquear_turma(db, empresa.turma_id)
    db.refresh(empresa)
    return _empresa_do_aluno(db, empresa_id, aluno)


@router.get("/empresas")
def minhas_empresas(db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno)):
    empresas = db.query(Empresa).filter(or_(
        Empresa.aluno_id == aluno.id,
        and_(Empresa.turma.has(Turma.modo_equipe.is_(True)), Empresa.membros.any(MembroEmpresa.aluno_id == aluno.id)),
    )).order_by(Empresa.id.desc()).all()
    matricula = db.get(MatriculaTurma, aluno.id)
    return [{"empresa": ser.empresa(e), "turma": ser.turma(e.turma)} for e in empresas if not matricula or e.turma_id == matricula.turma_id]


@router.post("/turmas/entrar", status_code=201)
def entrar_na_turma(
    dados: EntrarTurmaEntrada, db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno)
):
    turma = db.get(Turma, dados.turma_id) if dados.turma_id else db.query(Turma).filter(Turma.codigo == (dados.codigo or "").strip().upper()).first()
    if turma is None:
        raise HTTPException(404, "Turma não encontrada.")
    turma = matricular(db, aluno, turma.id)
    if turma.formacao_encerrada:
        raise HTTPException(422, "A formação das equipes foi encerrada. Procure o professor.")
    if turma.status != StatusTurma.ABERTA:
        raise HTTPException(422, "Esta turma já foi encerrada.")
    if turma.rodada_atual > 1:
        raise HTTPException(422, "A turma já começou. Peça ao professor para incluí-lo antes da 1ª rodada.")
    if (
        db.query(Empresa).filter(Empresa.turma_id == turma.id, Empresa.aluno_id == aluno.id).first()
        or db.query(MembroEmpresa).filter(MembroEmpresa.turma_id == turma.id, MembroEmpresa.aluno_id == aluno.id).first()
    ):
        raise HTTPException(409, "Você já tem uma empresa nesta turma.")

    perfil = perfil_inicial(dados.tipo_entrada_gem, dados.classe_dornelas)
    empresa = Empresa(
        turma_id=turma.id,
        aluno_id=aluno.id,
        nome=dados.nome_empresa.strip(),
        codigo_convite=novo_convite() if turma.modo_equipe else None,
        tipo_entrada_gem=dados.tipo_entrada_gem,
        classe_dornelas=dados.classe_dornelas,
        regime_tributario=dados.regime_tributario,
        caixa=turma.caixa_inicial,
        **perfil,
    )
    db.add(empresa)
    from ..motor.avancado import iniciar_empresa
    iniciar_empresa(empresa, turma)
    db.flush()
    if turma.modo_equipe:
        db.add(MembroEmpresa(empresa_id=empresa.id, turma_id=turma.id, aluno_id=aluno.id, cargos=["CEO"]))
        registrar(db, empresa, aluno, "CRIAR_EQUIPE")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Você já participa de uma empresa nesta turma.")
    db.refresh(empresa)
    return {"empresa": ser.empresa(empresa), "turma": ser.turma(turma), "equipe": dados_equipe(empresa, None, aluno)}


@router.post("/equipes/entrar", status_code=201)
def entrar_na_equipe(
    dados: EntrarEquipeEntrada, db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno),
):
    empresa = db.get(Empresa, dados.empresa_id) if dados.empresa_id else db.query(Empresa).filter(Empresa.codigo_convite == (dados.codigo or "").strip()).first()
    if empresa is None:
        raise HTTPException(404, "Convite de equipe não encontrado. Confira o código com o CEO.")
    turma = matricular(db, aluno, empresa.turma_id)
    db.refresh(empresa)
    if turma.formacao_encerrada:
        raise HTTPException(422, "A formação das equipes foi encerrada. Procure o professor.")
    if not turma.modo_equipe:
        raise HTTPException(422, "Esta turma usa empresas individuais.")
    if turma.status != StatusTurma.ABERTA or turma.rodada_atual != 1:
        raise HTTPException(422, "Só é possível ingressar na equipe antes do fechamento da primeira rodada.")
    if (
        db.query(MembroEmpresa).filter(MembroEmpresa.turma_id == turma.id, MembroEmpresa.aluno_id == aluno.id).first()
        or db.query(Empresa).filter(Empresa.turma_id == turma.id, Empresa.aluno_id == aluno.id).first()
    ):
        raise HTTPException(409, "Você já participa de uma empresa nesta turma.")
    if len(empresa.membros) >= 5:
        raise HTTPException(422, "Esta equipe já tem 5 alunos. Entre em outra equipe.")
    db.add(MembroEmpresa(empresa_id=empresa.id, turma_id=turma.id, aluno_id=aluno.id, cargos=[]))
    versao = invalidar_aprovacoes(db, empresa)
    registrar(db, empresa, aluno, "ENTRAR_EQUIPE", versao)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Você já participa de uma empresa nesta turma.")
    db.refresh(empresa)
    return {
        "empresa": ser.empresa(empresa), "turma": ser.turma(turma),
        "equipe": dados_equipe(empresa, decisao_atual(db, empresa), aluno),
    }


@router.put("/empresas/{empresa_id}/equipe")
def distribuir_cargos(
    empresa_id: int, dados: EquipeEntrada, db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno),
):
    empresa = _empresa_para_alterar(db, empresa_id, aluno)
    if not empresa.turma.modo_equipe:
        raise HTTPException(422, "Esta turma usa empresas individuais.")
    if aluno.id != (empresa.lider_id or empresa.aluno_id):
        raise HTTPException(403, "Somente o responsável pela equipe pode distribuir os cargos.")
    if empresa.turma.status != StatusTurma.ABERTA:
        raise HTTPException(422, "A turma foi encerrada.")
    if empresa.turma.rodada_atual != 1:
        raise HTTPException(422, "Distribua os cargos antes do fechamento da primeira rodada.")
    atribuicoes = {m.aluno_id: [cargo.value for cargo in m.cargos] for m in dados.membros}
    if len(atribuicoes) != len(dados.membros) or set(atribuicoes) != {m.aluno_id for m in empresa.membros}:
        raise HTTPException(422, "Informe todos os integrantes atuais, uma única vez cada.")
    for aluno_id, cargos in atribuicoes.items():
        if len(cargos) != len(set(cargos)):
            raise HTTPException(422, "Não repita o mesmo cargo para um integrante.")
        if ("CEO" in cargos) != (aluno_id == empresa.aluno_id):
            raise HTTPException(422, "O fundador da empresa deve permanecer como o único CEO.")
    todos_cargos = [cargo for cargos in atribuicoes.values() for cargo in cargos]
    if len(todos_cargos) != len(set(todos_cargos)):
        raise HTTPException(422, "Cada cargo deve ser atribuído a um único integrante; um aluno pode acumular cargos diferentes.")
    mudou = any(m.cargos != atribuicoes[m.aluno_id] for m in empresa.membros)
    if mudou:
        for membro in empresa.membros:
            membro.cargos = atribuicoes[membro.aluno_id]
        versao = invalidar_aprovacoes(db, empresa)
        registrar(db, empresa, aluno, "ALTERAR_CARGOS", versao, {"membros": [
            {"aluno_id": aluno_id, "cargos": cargos} for aluno_id, cargos in atribuicoes.items()
        ]})
    db.commit()
    db.refresh(empresa)
    return dados_equipe(empresa, decisao_atual(db, empresa), aluno)


@router.get("/empresas/{empresa_id}")
def painel(empresa_id: int, db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno)):
    empresa = _empresa_do_aluno(db, empresa_id, aluno)
    turma = empresa.turma
    decisao_atual = (
        db.query(Decisao)
        .filter(Decisao.empresa_id == empresa.id, Decisao.rodada == turma.rodada_atual)
        .first()
    )
    ultima_decisao = (
        db.query(Decisao)
        .filter(Decisao.empresa_id == empresa.id)
        .order_by(Decisao.rodada.desc())
        .first()
    )

    # Informação de mercado da última rodada: preço médio e participação de cada concorrente
    ids = [e.id for e in turma.empresas]
    ultima_rodada = turma.rodada_atual - 1
    concorrentes = []
    if ultima_rodada >= 1:
        resultados = (
            db.query(Resultado)
            .filter(Resultado.rodada == ultima_rodada, Resultado.empresa_id.in_(ids))
            .all()
        )
        nomes = {e.id: e.nome for e in turma.empresas}
        concorrentes = sorted(
            (
                {
                    "empresa": nomes[r.empresa_id],
                    "propria": r.empresa_id == empresa.id,
                    "preco": r.preco,
                    "participacao_mercado": r.participacao_mercado,
                }
                for r in resultados
            ),
            key=lambda linha: linha["participacao_mercado"],
            reverse=True,
        )

    posicao = next(
        (linha["posicao"] for linha in ser.ranking(turma) if linha["empresa_id"] == empresa.id), None
    )

    return {
        "empresa": ser.empresa(empresa),
        "turma": ser.turma(turma, completa=True),
        "decisao_atual": ser.decisao(decisao_atual) if decisao_atual and not decisao_atual.automatica else None,
        "ultima_decisao": ser.decisao(ultima_decisao),
        "resultados": [ser.resultado(r) for r in empresa.resultados],
        "eventos": [ser.evento(e) for e in turma.eventos],
        "mercado": concorrentes,
        "posicao_ranking": posicao,
        "total_empresas": len(turma.empresas),
        "equipe": dados_equipe(empresa, decisao_atual, aluno),
        "jornada": jornada_empresa(empresa),
        "pendencias_envio": pendencias_envio(empresa, DecisaoEntrada.model_validate({**ser.decisao(decisao_atual), "rascunho": True})) if decisao_atual else ["Prepare e salve a decisão da rodada."],
    }


def _validar_decisao(empresa: Empresa, dados: DecisaoEntrada) -> None:
    verificar_rodada(dados.rodada, empresa.turma,
                    obrigatoria=empresa.turma.modo_equipe or empresa.turma.modo_jogo != "LEGADO")
    if empresa.turma.modo_jogo != "LEGADO" and dados.simulacao is None:
        raise HTTPException(422, "Informe as decisões de operação deste modo de jogo.")
    if empresa.turma.modo_jogo != "STARTUP" and dados.simulacao and dados.simulacao.aporte:
        raise HTTPException(422, "Aportes de investidores estão disponíveis no modo Startup.")
    if empresa.turma.modo_jogo == "TRADICIONAL" and dados.simulacao and dados.simulacao.comprar_maquinas and empresa.turma.rodada_atual < 3:
        raise HTTPException(422, "Novos investimentos em máquinas estão disponíveis a partir do terceiro mês, após as duas primeiras rodadas.")
    if empresa.turma.status != StatusTurma.ABERTA:
        raise HTTPException(422, "A turma foi encerrada; não há mais rodadas para decidir.")
    if dados.simulacao and dados.simulacao.horas_extras:
        if empresa.turma.modo_jogo != "TRADICIONAL":
            raise HTTPException(422, "Horas extras de produção estão disponíveis no modo Empresa tradicional.")
        if empresa.funcionarios + dados.contratar - dados.demitir <= 0:
            raise HTTPException(422, "Horas extras exigem funcionários; você pode contratar nesta rodada.")
    if dados.demitir > empresa.funcionarios:
        raise HTTPException(422, f"Você só pode demitir até {empresa.funcionarios} funcionário(s).")
    if dados.amortizacao > empresa.divida + dados.emprestimo + 0.01:
        raise HTTPException(422, "A amortização não pode ser maior que a dívida.")


@router.post("/empresas/{empresa_id}/previsao")
def previa_decisao(
    empresa_id: int,
    dados: DecisaoEntrada,
    db: Session = Depends(get_db),
    aluno: Usuario = Depends(exigir_aluno),
):
    empresa = _empresa_do_aluno(db, empresa_id, aluno)
    from .mercado import validar_plano
    validar_plano(db, empresa, dados, rascunho=dados.rascunho)
    _validar_decisao(empresa, dados)
    return prever_decisao(empresa, Decisao(**dados.model_dump(exclude={"versao", "rodada", "rascunho"})), empresa.turma)


@router.put("/empresas/{empresa_id}/decisao")
def enviar_decisao(
    empresa_id: int,
    dados: DecisaoEntrada,
    db: Session = Depends(get_db),
    aluno: Usuario = Depends(exigir_aluno),
):
    empresa = _empresa_para_alterar(db, empresa_id, aluno)
    turma = empresa.turma
    exigir_lider(empresa, aluno)
    from ..prazos import validar_salvamento
    validar_salvamento(turma, dados.rodada)
    from .mercado import validar_plano
    validar_plano(db, empresa, dados, rascunho=dados.rascunho)
    _validar_decisao(empresa, dados)
    if not dados.rascunho:
        motivos = pendencias_envio(empresa, dados)
        if motivos:
            raise HTTPException(422, "Você não pode enviar a decisão final: " + " ".join(motivos))
    decisao = (
        db.query(Decisao)
        .filter(Decisao.empresa_id == empresa.id, Decisao.rodada == turma.rodada_atual)
        .first()
    )
    if decisao and decisao.enviada_em:
        raise HTTPException(403, "Decisão final enviada. Modo de leitura até a próxima rodada.")
    versao_atual = decisao.versao if decisao else 0
    verificar_versao(dados.versao, versao_atual, obrigatoria=turma.modo_equipe)
    valores = dados.model_dump(exclude={"versao", "rodada", "rascunho"})
    valores.update(
        automatica=0, versao=versao_atual + 1,
        enviada_em=None if dados.rascunho else agora(),
    )
    if decisao is None:
        decisao = Decisao(empresa_id=empresa.id, rodada=turma.rodada_atual, **valores)
        db.add(decisao)
        db.flush()
    else:
        atualizado = db.execute(
            update(Decisao).where(Decisao.id == decisao.id, Decisao.versao == versao_atual).values(**valores),
            execution_options={"synchronize_session": False},
        )
        if atualizado.rowcount != 1:
            raise HTTPException(409, "A decisão foi alterada. Atualize o painel antes de salvar.")
        db.refresh(decisao)
    if turma.modo_equipe:
        if dados.rascunho:
            registrar(db, empresa, aluno, "SALVAR_RASCUNHO", decisao.versao, snapshot_decisao(decisao))
        else:
            registrar_envio(db, empresa, decisao, aluno)
    db.commit()
    db.refresh(decisao)
    return ser.decisao(decisao)


@router.post("/empresas/{empresa_id}/aprovar")
def aprovar_decisao(
    empresa_id: int, dados: AprovarDecisaoEntrada,
    db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno),
):
    empresa = _empresa_para_alterar(db, empresa_id, aluno)
    exigir_lider(empresa, aluno)
    from ..prazos import validar_salvamento
    validar_salvamento(empresa.turma, dados.rodada)
    verificar_rodada(dados.rodada, empresa.turma, obrigatoria=True)
    if empresa.turma.status != StatusTurma.ABERTA:
        raise HTTPException(422, "A turma foi encerrada.")
    decisao = decisao_atual(db, empresa)
    if decisao is None:
        raise HTTPException(422, "Salve um rascunho antes de enviar a decisão final.")
    verificar_versao(dados.versao, decisao.versao)
    entrada = DecisaoEntrada.model_validate(ser.decisao(decisao))
    motivos = pendencias_envio(empresa, entrada)
    if motivos:
        raise HTTPException(422, "Você não pode enviar a decisão final: " + " ".join(motivos))
    from .mercado import validar_plano
    validar_plano(db, empresa, entrada)
    _validar_decisao(empresa, entrada)
    for campo, valor in entrada.model_dump(exclude={"versao", "rodada", "rascunho"}).items():
        setattr(decisao, campo, valor)
    decisao.enviada_em = agora()
    registrar_envio(db, empresa, decisao, aluno)
    db.commit()
    return dados_equipe(empresa, decisao, aluno)


class MatriculaEntrada(BaseModel):
    turma_id: int = Field(gt=0)


@router.get("/turmas")
def turmas_disponiveis(db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno)):
    m = db.get(MatriculaTurma, aluno.id)
    turmas = db.query(Turma).filter(Turma.visivel_ingresso.is_(True), Turma.formacao_encerrada.is_(False), Turma.rodada_atual == 1, Turma.status == StatusTurma.ABERTA).all()
    return [ser.turma(t) for t in turmas if not m or t.id in (m.turma_id, m.autorizada_turma_id)]


@router.get("/matricula")
def minha_matricula(db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno)):
    m = db.get(MatriculaTurma, aluno.id)
    return {"turma": ser.turma(db.get(Turma, m.turma_id)), "sala": sala(db, db.get(Turma, m.turma_id))} if m else None


@router.post("/matricula")
def entrar_matricula(dados: MatriculaEntrada, db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno)):
    turma = matricular(db, aluno, dados.turma_id)
    db.commit()
    return {"turma": ser.turma(turma), "sala": sala(db, turma)}


class LiderEntrada(BaseModel):
    aluno_id: int = Field(gt=0)
    rodada: int = Field(ge=1, le=60)


@router.post("/empresas/{empresa_id}/lider")
def escolher_lider(empresa_id: int, dados: LiderEntrada, db: Session = Depends(get_db), aluno: Usuario = Depends(exigir_aluno)):
    empresa = _empresa_para_alterar(db, empresa_id, aluno)
    verificar_rodada(dados.rodada, empresa.turma, True)
    if not empresa.turma.modo_equipe or empresa.turma.status != StatusTurma.ABERTA:
        raise HTTPException(422, "A equipe não está disponível para escolha de liderança.")
    ids = {m.aluno_id for m in empresa.membros}
    if not 3 <= len(ids) <= 5 or dados.aluno_id not in ids or aluno.id not in ids:
        raise HTTPException(422, "Reúna de 3 a 5 integrantes e escolha alguém da própria equipe.")
    if empresa.lider_id is None:
        votos = {**{k:v for k,v in (empresa.votos_lider or {}).items() if int(k) in ids and v in ids}, str(aluno.id): dados.aluno_id}
        empresa.votos_lider = votos
        if sum(v == dados.aluno_id for v in votos.values()) > len(ids) / 2:
            empresa.lider_id = dados.aluno_id
        registrar(db, empresa, aluno, "ESCOLHER_LIDER", detalhes={"escolhido": dados.aluno_id, "lider_id": empresa.lider_id})
    else:
        exigir_lider(empresa, aluno)
        if dados.aluno_id == empresa.lider_id:
            raise HTTPException(422, "Escolha outro integrante para a próxima rodada.")
        if empresa.turma.rodada_atual >= empresa.turma.total_rodadas:
            raise HTTPException(422, "Esta é a última rodada; não há próxima rodada para transferir.")
        if empresa.proximo_lider_id:
            raise HTTPException(409, "Já existe uma transferência programada para a próxima rodada.")
        empresa.proximo_lider_id = dados.aluno_id
        registrar(db, empresa, aluno, "TRANSFERIR_LIDER", detalhes={"proximo_lider_id": dados.aluno_id, "vigencia": empresa.turma.rodada_atual + 1})
    db.commit()
    return dados_equipe(empresa, decisao_atual(db, empresa), aluno)
