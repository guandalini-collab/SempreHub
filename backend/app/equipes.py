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
    conteudo["simulacao"] = deepcopy(decisao.simulacao)
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
    cargos = {cargo for membro in membros for cargo in (membro.cargos or [])}
    atribuicoes = Counter(cargo for membro in membros for cargo in (membro.cargos or []))
    duplicados = [cargo for cargo in CARGOS if atribuicoes[cargo] > 1]
    if duplicados:
        pendencias.append("Atribua cada cargo a um único integrante: " + ", ".join(duplicados) + ".")
    faltantes = [cargo for cargo in CARGOS if cargo not in cargos]
    if faltantes:
        pendencias.append("Distribua os cargos: " + ", ".join(faltantes) + ".")
    sem_cargos = [m.aluno.nome for m in membros if not m.cargos]
    if sem_cargos:
        pendencias.append("Atribua cargos a: " + ", ".join(sem_cargos) + ".")
    ceos = [m.aluno_id for m in membros if "CEO" in (m.cargos or [])]
    if ceos != [empresa.aluno_id]:
        pendencias.append("O fundador da empresa deve ser o único CEO.")
    if decisao is None or decisao.automatica:
        pendencias.append(f"Salve uma decisão para a rodada {empresa.turma.rodada_atual}.")
    elif incluir_aprovacoes:
        aprovados = {a.aluno_id for a in decisao.aprovacoes if a.versao == decisao.versao}
        faltam = [m.aluno.nome for m in membros if m.aluno_id not in aprovados]
        if faltam:
            pendencias.append("Aguardando aprovação de: " + ", ".join(faltam) + ".")
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
        "pode_gerenciar": bool(aluno and aluno.id == empresa.aluno_id),
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
