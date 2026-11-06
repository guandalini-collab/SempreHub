"""Regressões do motor de ocorrências individuais e auditáveis."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    ClasseDornelas,
    Decisao,
    Empresa,
    Papel,
    RegimeTributario,
    TipoEntradaGem,
    Turma,
    Usuario,
)
from app.motor import eventos_operacionais as eventos


def _banco_temporario():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


def test_sorteio_operacional_e_reprodutivel_sem_duplicar_na_mesma_semana(monkeypatch):
    engine, db = _banco_temporario()
    try:
        professor = Usuario(nome="Professor", email="professor@teste.local", senha_hash="x", papel=Papel.PROFESSOR)
        aluno = Usuario(nome="Aluno", email="aluno@teste.local", senha_hash="x", papel=Papel.ALUNO)
        turma = Turma(nome="Teste", codigo="EVENTOS", professor=professor, modo_jogo="TRADICIONAL", total_rodadas=12,
                      configuracao_simulacao={})
        empresa = Empresa(turma=turma, aluno=aluno, nome="Empresa teste", tipo_entrada_gem=TipoEntradaGem.OPORTUNIDADE,
                          classe_dornelas=ClasseDornelas.SERIAL, regime_tributario=RegimeTributario.MEI,
                          estado_simulacao={"maquinas": [{"capacidade": 100}]})
        db.add_all([professor, aluno, turma, empresa])
        db.flush()
        db.add(Decisao(empresa=empresa, rodada=1, preco=100, simulacao={"manutencao": 0}))
        db.commit()

        regra = eventos.RegraEvento(
            "TESTE_AUDITAVEL", "Finanças", "Evento de teste", "Ocorrência determinística.", 1.0, (1, 1), False,
            lambda fatores: True, lambda fatores: (1.0, {"condicao": "teste"}), lambda escala: {"custo": 10 * escala},
        )
        monkeypatch.setattr(eventos, "EVENTOS", (regra,))

        criados = eventos.gerar_para_rodada(db, turma, [empresa], 2)
        db.flush()
        assert len(criados) == 1
        assert criados[0].semente
        assert criados[0].impacto == {"custo": 10.0}
        assert eventos.gerar_para_rodada(db, turma, [empresa], 2) == []
        efeitos, ativos = eventos.efeitos_ativos(db, empresa.id, 2)
        assert len(ativos) == 1
        assert efeitos["custo"] == 10.0
    finally:
        db.close()
        Base.metadata.drop_all(engine)
