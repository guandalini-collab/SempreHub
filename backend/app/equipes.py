"""Composição, assinaturas de decisões e participação individual das equipes."""

import secrets
from collections import Counter
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from .models import CargoEquipe, Decisao, Empresa, MembroEmpresa, RegistroEquipe, Turma, Usuario


CARGOS = [cargo.value for cargo in CargoEquipe]
CAMPOS_DECISAO = (
    "preco", "marketing", "pd", "networking", "contratar", "demitir",
    "emprestimo", "amortizacao", "regime_solicitado",
)


def novo_convite() -> str:
    # Um convite dá acesso ao ingresso, portanto não deriva de IDs nem do código da turma.
    return secrets.token_urlsafe(24)


def bloquear_turma(db: Session, turma_id: int) -> Turma:
    """Serializa alterações e fechamento, inclusive no SQLite sem FOR UPDATE.

    O UPDATE inócuo adquire o bloqueio de escrita antes de reler o estado. A mesma
    ordem (turma, depois empresa) evita aprovar ou salvar durante o fechamento.
    """
    db.execute(
        update(Turma).where(Turma.id == turma_id).values(rodada_atual=Turma.rodada_atual),
        execution_options={"synchronize_session": False},
    )
    turma = db.query(Turma).filter(Turma.id == turma_id).populate_existing().first()
    if turma is None:
        raise HTTPException(404, "Turma não encontrada.")
    return turma


def decisao_atual(db: Session, empresa: Empresa) -> Optional[Decisao]:
    return db.query(Decisao).filter(
        Decisao.empresa_id == empresa.id,
        Decisao.rodada == empresa.turma.rodada_atual,
    ).first()


def verificar_versao(esperada: Optional[int], atual: int, obrigatoria: bool = True) -> None:
    if esperada is None:
        if obrigatoria:
            raise HTTPException(422, "Informe a versão da decisão. Atualize o painel antes de salvar.")
        return
    if esperada != atual:
        raise HTTPException(
            409,
            f"A decisão foi alterada por outro integrante (versão atual: {atual}). "
            "Atualize o painel e confira os dados antes de tentar novamente.",
        )


def verificar_rodada(esperada: Optional[int], turma: Turma, obrigatoria: bool = False) -> None:
    if esperada is None and obrigatoria:
        raise HTTPException(422, "Informe a rodada da decisão. Atualize o painel antes de enviar.")
    if esperada is not None and esperada != turma.rodada_atual:
        raise HTTPException(
            409,
            f"A turma avançou para a rodada {turma.rodada_atual}. "
            "Atualize o painel antes de enviar novas decisões.",
        )


def snapshot_decisao(decisao: Decisao) -> dict:
    conteudo = {campo: getattr(decisao, campo) for campo in CAMPOS_DECISAO}
    if conteudo["regime_solicitado"] is not None:
        conteudo["regime_solicitado"] = conteudo["regime_solicitado"].value
    conteudo.update(rodada=decisao.rodada, versao=decisao.versao)
    from copy import deepcopy
    conteudo["analise_financeira"] = decisao.analise_financeira
    conteudo["simulacao"] = deepcopy(decisao.simulacao)
    conteudo["plano_comercial"] = deepcopy(decisao.plano_comercial)
    conteudo["revisao_areas"] = deepcopy(decisao.revisao_areas or {})
    return conteudo


def registrar(
    db: Session, empresa: Empresa, aluno: Usuario, acao: str,
    versao: int = 0, detalhes: Optional[dict] = None,
) -> None:
    db.add(RegistroEquipe(
        empresa_id=empresa.id, aluno_id=aluno.id,
        rodada=empresa.turma.rodada_atual, versao=versao,
        acao=acao, detalhes=detalhes or {},
    ))


def registrar_login(db: Session, usuario: Usuario) -> None:
    empresas = db.query(Empresa).join(
        MembroEmpresa, MembroEmpresa.empresa_id == Empresa.id,
    ).join(Turma, Turma.id == Empresa.turma_id).filter(
        MembroEmpresa.aluno_id == usuario.id, Turma.modo_equipe.is_(True),
    ).all()
    for empresa in empresas:
        decisao = decisao_atual(db, empresa)
        registrar(db, empresa, usuario, "LOGIN", decisao.versao if decisao else 0)


def invalidar_aprovacoes(db: Session, empresa: Empresa) -> int:
    """Mudar a composição/cargos exige nova assinatura, sem excluir as anteriores."""
    decisao = decisao_atual(db, empresa)
    if decisao is None:
        return 0
    db.execute(
        update(Decisao).where(Decisao.id == decisao.id).values(
            versao=Decisao.versao + 1, enviada_em=None,
        ), execution_options={"synchronize_session": False},
    )
    db.refresh(decisao)
    return decisao.versao


def pendencias_equipe(
    empresa: Empresa, decisao: Optional[Decisao], incluir_aprovacoes: bool = True,
) -> list:
    membros = empresa.membros
    pendencias = []
    if not 3 <= len(membros) <= 5:
        pendencias.append(f"Reúna de 3 a 5 alunos (atualmente {len(membros)}).")
    if empresa.lider_id is None:
        pendencias.append("Escolham o líder da equipe.")
    if decisao is None or decisao.automatica:
        pendencias.append(f"Salve uma decisão para a rodada {empresa.turma.rodada_atual}.")
    elif incluir_aprovacoes and not decisao.enviada_em:
        pendencias.append("O líder ainda não enviou a decisão final.")
    return pendencias


def pendencias_fechamento(db: Session, turma: Turma) -> list:
    if not turma.modo_equipe:
        return []
    pendencias = []
    for empresa in turma.empresas:
        motivos = pendencias_equipe(empresa, decisao_atual(db, empresa))
        if motivos:
            pendencias.append(empresa.nome + ": " + " ".join(motivos))
    return pendencias


def dados_equipe(
    empresa: Empresa, decisao: Optional[Decisao], aluno: Optional[Usuario] = None,
) -> Optional[dict]:
    if not empresa.turma.modo_equipe:
        return None
    membros = [
        {"aluno_id": m.aluno_id, "nome": m.aluno.nome, "cargos": m.cargos or []}
        for m in empresa.membros
    ]
    aprovacoes = [
        {
            "aluno_id": a.aluno_id, "nome": a.aluno.nome, "versao": a.versao,
            "aprovado_em": a.aprovado_em.isoformat() + "Z",
        }
        for a in (decisao.aprovacoes if decisao else [])
        if a.versao == decisao.versao
    ]
    pendencias = pendencias_equipe(empresa, decisao)
    return {
        "codigo_convite": empresa.codigo_convite,
        "membros": membros,
        "meus_cargos": next((m["cargos"] for m in membros if aluno and m["aluno_id"] == aluno.id), []),
        "pode_gerenciar": bool(aluno and aluno.id == (empresa.lider_id or empresa.aluno_id)),
        "pode_decidir": bool(aluno and aluno.id == empresa.lider_id),
        "lider_id": empresa.lider_id,
        "proximo_lider_id": empresa.proximo_lider_id,
        "transferencia_rodada": empresa.turma.rodada_atual + 1 if empresa.proximo_lider_id else None,
        "votos_lider": empresa.votos_lider or {},
        "versao_decisao": decisao.versao if decisao else 0,
        "aprovacoes": aprovacoes,
        "aprovada_por_mim": bool(aluno and any(a["aluno_id"] == aluno.id for a in aprovacoes)),
        "pronta": not pendencias,
        "pendencias": pendencias,
        "historico": [
            {
                "acao": r.acao, "aluno_id": r.aluno_id, "aluno": r.aluno.nome,
                "rodada": r.rodada, "versao": r.versao,
                "data": r.data.isoformat() + "Z", "detalhes": r.detalhes,
            }
            for r in empresa.registros_equipe
        ],
    }


def exigir_lider(empresa, aluno):
    if empresa.turma.modo_equipe and empresa.lider_id != aluno.id:
        raise HTTPException(403, "Somente o líder escolhido pela equipe pode salvar e enviar decisões. Você tem acesso de visualização.")


def pendencias_envio(empresa, dados):
    """Zeros opcionais são válidos; a revisão comprova a escolha consciente."""
    motivos = pendencias_equipe(empresa, None, False)[:]
    motivos = [m for m in motivos if not m.startswith("Salve uma decisão")]
    if not empresa.turma.modo_equipe:
        motivos = []
    areas = {"decisoes": "Produtos e marketing", "financas": "Finanças", "producao": "Produção e operação"}
    if empresa.turma.modo_jogo == "TRADICIONAL":
        areas["logistica"] = "Logística"
    for chave, titulo in areas.items():
        if not (dados.revisao_areas or {}).get(chave):
            motivos.append("Revise e confirme a área: " + titulo + ".")
    if not (dados.analise_financeira or "").strip():
        motivos.append("Preencha a análise financeira da equipe.")
    plano = dados.plano_comercial
    if plano:
        a = plano.analises
        if not a or not a.swot.diretriz:
            motivos.append("Escolha a diretriz após interpretar a SWOT.")
        if not a or not a.segmentacao.geografica or not a.segmentacao.canais or not a.segmentacao.cobertura or a.segmentacao.preco_maximo is None:
            motivos.append("Complete o público-alvo: localização, canais, cobertura e preço máximo.")
        if not a or set(p.produto_id for p in a.bcg) != set(p.produto_id for p in plano.produtos):
            motivos.append("Preencha a matriz BCG para todos os produtos.")
        if a and any(p.base == "PROJECAO" and not p.premissas.strip() for p in a.bcg):
            motivos.append("Informe as premissas das projeções da matriz BCG.")
        for p in plano.produtos:
            if not p.revisado:
                motivos.append("Revise o mix do produto: " + (p.produto_nome or p.produto_id) + ".")
    return motivos


def registrar_envio(db, empresa, decisao, aluno):
    from .models import AprovacaoDecisao
    if not any(a.versao == decisao.versao and a.aluno_id == aluno.id for a in decisao.aprovacoes):
        conteudo = snapshot_decisao(decisao)
        conteudo.update(tipo="ENVIO_LIDER", lider_id=aluno.id, membros=[{"aluno_id":m.aluno_id,"nome":m.aluno.nome,"cargos":m.cargos or []} for m in empresa.membros])
        decisao.aprovacoes.append(AprovacaoDecisao(empresa_id=empresa.id, aluno_id=aluno.id, rodada=decisao.rodada, versao=decisao.versao, conteudo=conteudo))
    registrar(db, empresa, aluno, "ENVIAR_DECISAO", decisao.versao, snapshot_decisao(decisao))
