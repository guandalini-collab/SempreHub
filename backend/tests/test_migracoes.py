"""Migrações versionadas preservam contas e rodadas em SQLite e PostgreSQL."""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import Column, DateTime, Enum, Integer, MetaData, String, Table, create_engine, inspect, select, text
from sqlalchemy.orm import Session

import app.migracoes as migracoes
from app.database import Base, engine, get_db
from app.main import app
from app.models import Papel, Usuario

from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar


_HEAD = "0003_versao_sessao"


@pytest.fixture()
def banco_migracoes(tmp_path):
    """Cada caso usa um arquivo ou schema descartável, nunca os dados da aplicação."""
    if engine.dialect.name == "postgresql":
        schema = f"teste_migracoes_{uuid4().hex}"
        with engine.begin() as conexao:
            conexao.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        banco = create_engine(
            engine.url,
            connect_args={"options": f"-csearch_path={schema}"},
            pool_pre_ping=True,
        )
        try:
            yield banco
        finally:
            banco.dispose()
            with engine.begin() as conexao:
                conexao.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
    else:
        banco = create_engine(
            f"sqlite:///{tmp_path / 'migracoes.db'}",
            connect_args={"check_same_thread": False},
        )
        try:
            yield banco
        finally:
            banco.dispose()


@contextmanager
def _cliente_no_banco(banco):
    def sessao_temporaria():
        with Session(banco) as sessao:
            yield sessao

    anterior = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = sessao_temporaria
    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        if anterior is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = anterior


def _snapshot(banco):
    """Compara inclusive hashes, versões de sessão e colunas fora das respostas HTTP."""
    metadata = MetaData()
    metadata.reflect(bind=banco)
    with banco.connect() as conexao:
        return {
            nome: [dict(linha) for linha in conexao.execute(select(tabela).order_by(tabela.c.id)).mappings()]
            for nome, tabela in metadata.tables.items()
            if nome != "alembic_version"
        }


def _confirmar_head(banco):
    scripts = ScriptDirectory.from_config(migracoes.configuracao_alembic())
    assert scripts.get_heads() == [_HEAD]
    with banco.connect() as conexao:
        assert MigrationContext.configure(conexao).get_current_heads() == (_HEAD,)


def _criar_usuarios_legado(banco):
    usuarios = Table(
        "usuarios",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("nome", String(120), nullable=False),
        Column("email", String(200), nullable=False, unique=True, index=True),
        Column("senha_hash", String(300), nullable=False),
        Column("papel", Enum(Papel), nullable=False),
        Column("criado_em", DateTime),
    )
    usuarios.create(bind=banco)
    return usuarios


def test_banco_vazio_chega_ao_head_e_corresponde_aos_modelos(banco_migracoes):
    assert inspect(banco_migracoes).get_table_names() == []
    migracoes.preparar_banco(banco_migracoes)
    _confirmar_head(banco_migracoes)
    with banco_migracoes.connect() as conexao:
        contexto = MigrationContext.configure(
            conexao,
            opts={"compare_type": True, "compare_server_default": True},
        )
        assert compare_metadata(contexto, Base.metadata) == []


def test_adota_banco_populado_sem_versao_e_continua_a_segunda_rodada(banco_migracoes):
    # Simula exatamente o schema que create_all deixou na versão anterior.
    Base.metadata.create_all(bind=banco_migracoes)
    assert "alembic_version" not in inspect(banco_migracoes).get_table_names()
    with _cliente_no_banco(banco_migracoes) as cliente:
        professor = cadastrar(cliente, "Prof. Migração", "migracao@iffarroupilha.edu.br", "PROFESSOR", "codigo-teste")
        turma = _criar_turma(cliente, professor, total_rodadas=2)
        aluno = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
        empresa_id = _entrar(cliente, aluno, turma["codigo"], "Ana Doces", regime="SIMPLES_NACIONAL")
        empresa_url = f"/api/aluno/empresas/{empresa_id}"
        fechar_url = f"/api/professor/turmas/{turma['id']}/fechar-rodada"
        resposta = cliente.get("/api/auth/eu", headers=aluno)
        assert resposta.status_code == 200
        aluno_id = resposta.json()["id"]
        # Uma versão não zero comprova que a adoção não reinicia sessões revogadas.
        redefinicao = cliente.post(
            f"/api/professor/alunos/{aluno_id}/redefinir-senha",
            headers=professor,
            json={"nova_senha": "nova-senha-segura"},
        )
        assert redefinicao.status_code == 200
        login = cliente.post("/api/auth/login", json={"email": "ana@aluno.iffar.edu.br", "senha": "nova-senha-segura"})
        assert login.status_code == 200
        aluno = {"Authorization": f"Bearer {login.json()['token']}"}
        decisao = cliente.put(
            f"{empresa_url}/decisao",
            headers=aluno,
            json={"preco": 95, "contratar": 1, "emprestimo": 12000, "marketing": 500, "pd": 300},
        )
        assert decisao.status_code == 200
        assert cliente.post(fechar_url, headers=professor, json={"evento": "GREVE_LOGISTICA"}).status_code == 200
        resposta = cliente.get(empresa_url, headers=aluno)
        assert resposta.status_code == 200
        painel_antes = resposta.json()
        assert painel_antes["turma"]["rodada_atual"] == 2
        assert painel_antes["empresa"]["divida"] == 12000
        antes = _snapshot(banco_migracoes)
        assert next(usuario for usuario in antes["usuarios"] if usuario["id"] == aluno_id)["versao_sessao"] == 1
        assert len(antes["decisoes"]) == len(antes["resultados"]) == len(antes["eventos_rodada"]) == 1

        for _ in range(2):
            migracoes.preparar_banco(banco_migracoes)
            _confirmar_head(banco_migracoes)
            assert _snapshot(banco_migracoes) == antes
        resposta = cliente.get(empresa_url, headers=aluno)
        assert resposta.status_code == 200
        assert resposta.json() == painel_antes
        novo_login = cliente.post("/api/auth/login", json={"email": "ana@aluno.iffar.edu.br", "senha": "nova-senha-segura"})
        assert novo_login.status_code == 200

        decisao = cliente.put(f"{empresa_url}/decisao", headers=aluno, json={"preco": 105, "amortizacao": 2000})
        assert decisao.status_code == 200
        assert decisao.json()["rodada"] == 2
        assert cliente.post(fechar_url, headers=professor, json={"evento": "NENHUM"}).status_code == 200
        resposta = cliente.get(empresa_url, headers=aluno)
        assert resposta.status_code == 200
        final = resposta.json()
        assert final["turma"]["status"] == "ENCERRADA"
        assert [resultado["rodada"] for resultado in final["resultados"]] == [1, 2]
        assert final["resultados"][0] == painel_antes["resultados"][0]
        assert final["eventos"][0] == painel_antes["eventos"][0]
        assert final["empresa"]["divida"] == 10000
        depois = _snapshot(banco_migracoes)
        assert depois["usuarios"] == antes["usuarios"]
        assert depois["decisoes"][0] == antes["decisoes"][0]


def test_revisao_anterior_e_atualizada_sem_perder_contas(banco_migracoes):
    configuracao = migracoes.configuracao_alembic()
    with banco_migracoes.begin() as conexao:
        configuracao.attributes["connection"] = conexao
        command.upgrade(configuracao, "0002_contas_teste")
        conexao.execute(
            text("INSERT INTO usuarios (id, nome, email, senha_hash, papel) VALUES (1, :nome, :email, :hash, 'PROFESSOR')"),
            {"nome": "Prof. Migração", "email": "prof@iffarroupilha.edu.br", "hash": "hash-professor-preservado"},
        )
        conexao.execute(
            text("INSERT INTO usuarios (id, nome, email, senha_hash, papel, criado_por_id) VALUES (2, :nome, :email, :hash, 'ALUNO', 1)"),
            {"nome": "Aluno de teste", "email": "teste@exemplo.invalid", "hash": "hash-aluno-preservado"},
        )
    assert "versao_sessao" not in {coluna["name"] for coluna in inspect(banco_migracoes).get_columns("usuarios")}
    antes = _snapshot(banco_migracoes)

    migracoes.preparar_banco(banco_migracoes)
    _confirmar_head(banco_migracoes)
    depois = _snapshot(banco_migracoes)
    for usuario in depois["usuarios"]:
        assert usuario.pop("versao_sessao") == 0
    assert depois == antes
    with Session(banco_migracoes) as sessao:
        assert sessao.get(Usuario, 2).criado_por_id == 1


def test_schema_legado_com_so_usuarios_recebe_tabelas_e_colunas_faltantes(banco_migracoes):
    usuarios = _criar_usuarios_legado(banco_migracoes)
    with banco_migracoes.begin() as conexao:
        conexao.execute(
            usuarios.insert(),
            {"id": 1, "nome": "Ana", "email": "ana@aluno.iffar.edu.br", "senha_hash": "hash-legado-preservado", "papel": Papel.ALUNO},
        )
    antes = _snapshot(banco_migracoes)["usuarios"][0]

    migracoes.preparar_banco(banco_migracoes)
    _confirmar_head(banco_migracoes)
    assert set(Base.metadata.tables).issubset(inspect(banco_migracoes).get_table_names())
    depois = _snapshot(banco_migracoes)["usuarios"][0]
    assert depois.pop("criado_por_id") is None
    assert depois.pop("versao_sessao") == 0
    assert depois == antes
    with banco_migracoes.begin() as conexao:
        conexao.execute(
            usuarios.insert(),
            {"id": 2, "nome": "Bia", "email": "bia@aluno.iffar.edu.br", "senha_hash": "hash-novo", "papel": Papel.ALUNO},
        )
        assert conexao.execute(text("SELECT versao_sessao FROM usuarios WHERE id = 2")).scalar_one() == 0


def test_schema_incompativel_e_bloqueado_sem_registrar_revisao(banco_migracoes):
    with banco_migracoes.begin() as conexao:
        conexao.execute(text("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, apelido VARCHAR(120) NOT NULL)"))
        conexao.execute(text("INSERT INTO usuarios (id, apelido) VALUES (1, 'Dado a preservar')"))
    antes = _snapshot(banco_migracoes)

    with pytest.raises(RuntimeError):
        migracoes.preparar_banco(banco_migracoes)
    assert _snapshot(banco_migracoes)["usuarios"] == antes["usuarios"]
    with banco_migracoes.connect() as conexao:
        assert MigrationContext.configure(conexao).get_current_heads() == ()


def test_migracao_respeita_transacao_existente_e_seu_rollback(banco_migracoes):
    usuarios = _criar_usuarios_legado(banco_migracoes)
    colunas_antes = {coluna["name"] for coluna in inspect(banco_migracoes).get_columns("usuarios")}
    antes = _snapshot(banco_migracoes)
    configuracao = migracoes.configuracao_alembic()

    with banco_migracoes.connect() as conexao:
        transacao = conexao.begin()
        conexao.execute(
            usuarios.insert(),
            {"id": 1, "nome": "Ana", "email": "ana@aluno.iffar.edu.br", "senha_hash": "hash-transacao", "papel": Papel.ALUNO},
        )
        # O INSERT já iniciou a transação física no sqlite3, além da SQLAlchemy.
        configuracao.attributes["connection"] = conexao
        command.upgrade(configuracao, "head")
        assert transacao.is_active
        assert conexao.in_transaction()
        assert MigrationContext.configure(conexao).get_current_heads() == (_HEAD,)
        assert "versao_sessao" in {coluna["name"] for coluna in inspect(conexao).get_columns("usuarios")}
        transacao.rollback()
        assert not conexao.in_transaction()

    # Nenhuma escrita, versão ou alteração de estrutura escapou do rollback.
    assert inspect(banco_migracoes).get_table_names() == ["usuarios"]
    assert {coluna["name"] for coluna in inspect(banco_migracoes).get_columns("usuarios")} == colunas_antes
    assert _snapshot(banco_migracoes) == antes
    with banco_migracoes.connect() as conexao:
        assert MigrationContext.configure(conexao).get_current_heads() == ()


def test_duas_inicializacoes_em_processos_preservam_dados_e_revisao(banco_migracoes, tmp_path):
    usuarios = _criar_usuarios_legado(banco_migracoes)
    with banco_migracoes.begin() as conexao:
        conexao.execute(
            usuarios.insert(),
            {"id": 1, "nome": "Ana", "email": "ana@aluno.iffar.edu.br", "senha_hash": "hash-concorrente", "papel": Papel.ALUNO},
        )
    antes = _snapshot(banco_migracoes)["usuarios"][0]
    barreira = tmp_path / "barreira"
    barreira.mkdir()
    ambiente = dict(os.environ)
    ambiente["DATABASE_URL"] = banco_migracoes.url.render_as_string(hide_password=False)
    ambiente["SEMPREHUB_MIGRACOES_BARREIRA"] = str(barreira)
    if banco_migracoes.dialect.name == "postgresql":
        with banco_migracoes.connect() as conexao:
            ambiente["SEMPREHUB_MIGRACOES_SCHEMA"] = conexao.execute(text("SELECT current_schema()")).scalar_one()
    else:
        ambiente.pop("SEMPREHUB_MIGRACOES_SCHEMA", None)

    programa = """
import os
import time
from pathlib import Path

from sqlalchemy import create_engine
from app.migracoes import preparar_banco

schema = os.getenv('SEMPREHUB_MIGRACOES_SCHEMA')
argumentos = {'options': f'-csearch_path={schema}'} if schema else {'check_same_thread': False}
banco = create_engine(os.environ['DATABASE_URL'], connect_args=argumentos)
barreira = Path(os.environ['SEMPREHUB_MIGRACOES_BARREIRA'])
(barreira / (os.environ['SEMPREHUB_MIGRACOES_PROCESSO'] + '.pronto')).write_text('pronto')
limite = time.monotonic() + 15
while len(list(barreira.glob('*.pronto'))) != 2:
    if time.monotonic() >= limite:
        raise RuntimeError('O segundo processo de teste não chegou à barreira.')
    time.sleep(0.02)
preparar_banco(banco)
banco.dispose()
"""
    processos = []
    try:
        for indice in range(2):
            ambiente_processo = dict(ambiente, SEMPREHUB_MIGRACOES_PROCESSO=str(indice))
            processos.append(
                subprocess.Popen(
                    [sys.executable, "-c", programa],
                    cwd=Path(migracoes.__file__).resolve().parents[1],
                    env=ambiente_processo,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            )
        # Apenas o acompanhamento dos subprocessos usa threads: cada Alembic
        # executa em seu próprio processo e possui seus próprios objetos globais.
        with ThreadPoolExecutor(max_workers=2) as executor:
            acompanhamentos = [executor.submit(processo.communicate, timeout=30) for processo in processos]
            for processo, acompanhamento in zip(processos, acompanhamentos):
                _, erros = acompanhamento.result()
                assert processo.returncode == 0, erros
    finally:
        for processo in processos:
            if processo.poll() is None:
                processo.kill()
                processo.communicate()

    _confirmar_head(banco_migracoes)
    depois = _snapshot(banco_migracoes)["usuarios"][0]
    assert depois.pop("criado_por_id") is None
    assert depois.pop("versao_sessao") == 0
    assert depois == antes
