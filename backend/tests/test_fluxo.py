import random

from app.motor.tributos import aliquota_efetiva_simples, calcular_imposto, rbt12
from app.models import RegimeTributario

from .conftest import cadastrar


# ---------------------------------------------------------------------------
# Cadastro e acesso
# ---------------------------------------------------------------------------
def test_aluno_precisa_de_email_institucional(cliente):
    r = cliente.post(
        "/api/auth/cadastro",
        json={"nome": "Fulano", "email": "fulano@gmail.com", "senha": "senha-segura"},
    )
    assert r.status_code == 422
    assert "aluno.iffarroupilha.edu.br" in r.json()["detail"]


def test_aluno_aceita_os_dois_dominios(cliente):
    cadastrar(cliente, "Ana", "ana@aluno.iffarroupilha.edu.br")
    cadastrar(cliente, "Bia", "bia@aluno.iffar.edu.br")


def test_professor_exige_codigo_docente(cliente):
    r = cliente.post(
        "/api/auth/cadastro",
        json={
            "nome": "Prof",
            "email": "p@iffarroupilha.edu.br",
            "senha": "senha-segura",
            "papel": "PROFESSOR",
            "codigo_docente": "errado",
        },
    )
    assert r.status_code == 403


def test_aluno_nao_se_cadastra_como_professor(cliente):
    r = cliente.post(
        "/api/auth/cadastro",
        json={
            "nome": "Aluno",
            "email": "x@aluno.iffar.edu.br",
            "senha": "senha-segura",
            "papel": "PROFESSOR",
            "codigo_docente": "codigo-teste",
        },
    )
    assert r.status_code == 422


def test_login_e_rotas_protegidas(cliente, professor):
    cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    r = cliente.post("/api/auth/login", json={"email": "ANA@aluno.iffar.edu.br", "senha": "senha-segura"})
    assert r.status_code == 200
    token = {"Authorization": f"Bearer {r.json()['token']}"}
    assert cliente.get("/api/professor/turmas", headers=token).status_code == 403
    assert cliente.get("/api/aluno/empresas").status_code == 401
    assert cliente.post("/api/auth/login", json={"email": "ana@aluno.iffar.edu.br", "senha": "x"}).status_code == 401


# ---------------------------------------------------------------------------
# Jogo completo
# ---------------------------------------------------------------------------
def _criar_turma(cliente, professor, **parametros):
    r = cliente.post("/api/professor/turmas", headers=professor, json={"nome": "Empreendedorismo 2026", **parametros})
    assert r.status_code == 201, r.text
    return r.json()


def _entrar(cliente, aluno, codigo, nome, regime="MEI", classe="SERIAL"):
    r = cliente.post(
        "/api/aluno/turmas/entrar",
        headers=aluno,
        json={
            "codigo": codigo.lower(),
            "nome_empresa": nome,
            "tipo_entrada_gem": "OPORTUNIDADE",
            "classe_dornelas": classe,
            "regime_tributario": regime,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["empresa"]["id"]


def test_rodada_completa_com_mercado_compartilhado(cliente, professor):
    turma = _criar_turma(cliente, professor, total_rodadas=3)
    a1 = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    a2 = cadastrar(cliente, "Bruno", "bruno@aluno.iffarroupilha.edu.br")
    e1 = _entrar(cliente, a1, turma["codigo"], "Ana Doces", regime="SIMPLES_NACIONAL")
    e2 = _entrar(cliente, a2, turma["codigo"], "Bruno Doces", regime="SIMPLES_NACIONAL")

    # Ana cobra mais barato; Bruno não envia decisão
    r = cliente.put(f"/api/aluno/empresas/{e1}/decisao", headers=a1, json={"preco": 90, "contratar": 1})
    assert r.status_code == 200, r.text

    detalhe = cliente.get(f"/api/professor/turmas/{turma['id']}", headers=professor).json()
    enviados = {e["nome"]: e["decisao_enviada"] for e in detalhe["empresas"]}
    assert enviados == {"Ana Doces": True, "Bruno Doces": False}

    r = cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "NENHUM"})
    assert r.status_code == 200, r.text
    assert r.json()["turma"]["rodada_atual"] == 2

    p1 = cliente.get(f"/api/aluno/empresas/{e1}", headers=a1).json()
    p2 = cliente.get(f"/api/aluno/empresas/{e2}", headers=a2).json()
    r1, r2 = p1["resultados"][0], p2["resultados"][0]

    # Mercado compartilhado: as participações somam 100% e o preço menor ganha mais mercado
    assert abs(r1["participacao_mercado"] + r2["participacao_mercado"] - 1) < 1e-9
    assert r1["participacao_mercado"] > r2["participacao_mercado"]
    assert any("repetiu" in alerta for alerta in r2["alertas"])

    # O DRE fecha com o caixa
    dre = r1["dre"]
    despesas = sum(v for k, v in dre.items() if k not in ("receita", "lucro_liquido"))
    assert abs(dre["receita"] - despesas - dre["lucro_liquido"]) < 1e-6
    assert abs(20000 + dre["lucro_liquido"] - r1["caixa_final"]) < 1e-6

    # Simples Nacional paga imposto (antes só o MEI pagava)
    assert dre["impostos"] > 0
    # Início de atividade: RBT12 = receita do mês × 12
    assert abs(r1["aliquota_efetiva"] - aliquota_efetiva_simples(dre["receita"] * 12)) < 1e-9
    assert abs(dre["impostos"] - dre["receita"] * r1["aliquota_efetiva"]) < 1e-6

    # Aluno vê a decisão anterior como base e não vê dados de outro aluno
    assert p1["ultima_decisao"]["preco"] == 90
    assert cliente.get(f"/api/aluno/empresas/{e2}", headers=a1).status_code == 404

    # Encerramento da turma após o total de rodadas
    for _ in range(2):
        cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "SORTEAR"})
    final = cliente.get(f"/api/professor/turmas/{turma['id']}", headers=professor).json()
    assert final["turma"]["status"] == "ENCERRADA"
    assert len(final["eventos"]) == 3
    assert [linha["posicao"] for linha in final["ranking"]] == [1, 2]
    r = cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "NENHUM"})
    assert r.status_code == 422

    csv = cliente.get(f"/api/professor/turmas/{turma['id']}/exportar.csv", headers=professor)
    assert csv.status_code == 200
    assert csv.text.count("\n") == 1 + 2 * 3


def test_professor_nao_ve_turma_de_outro(cliente, professor):
    turma = _criar_turma(cliente, professor)
    outro = cadastrar(cliente, "Outro", "outro@iffar.edu.br", "PROFESSOR", "codigo-teste")
    assert cliente.get(f"/api/professor/turmas/{turma['id']}", headers=outro).status_code == 404


def test_teto_do_mei_e_desenquadramento(cliente, professor):
    # Mercado grande para estourar o teto do MEI rapidamente
    turma = _criar_turma(cliente, professor, demanda_base_por_empresa=600, produtividade_por_pessoa=400)
    aluno = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    e = _entrar(cliente, aluno, turma["codigo"], "Ana MEI", regime="MEI")
    for _ in range(3):
        cliente.put(f"/api/aluno/empresas/{e}/decisao", headers=aluno, json={"preco": 100})
        cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "NENHUM"})
    painel = cliente.get(f"/api/aluno/empresas/{e}", headers=aluno).json()
    assert painel["empresa"]["regime_tributario"] == "SIMPLES_NACIONAL"
    alertas = " ".join(a for r in painel["resultados"] for a in r["alertas"])
    assert "Desenquadramento" in alertas or "Teto do MEI" in alertas


def test_mei_com_dois_empregados_e_desenquadrado(cliente, professor):
    turma = _criar_turma(cliente, professor)
    aluno = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    e = _entrar(cliente, aluno, turma["codigo"], "Ana MEI", regime="MEI")
    cliente.put(f"/api/aluno/empresas/{e}/decisao", headers=aluno, json={"preco": 100, "contratar": 2})
    cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "NENHUM"})
    painel = cliente.get(f"/api/aluno/empresas/{e}", headers=aluno).json()
    assert painel["empresa"]["regime_tributario"] == "SIMPLES_NACIONAL"


def test_emprestimo_juros_e_selic(cliente, professor):
    turma = _criar_turma(cliente, professor)
    aluno = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    e = _entrar(cliente, aluno, turma["codigo"], "Ana", regime="SIMPLES_NACIONAL")
    cliente.put(f"/api/aluno/empresas/{e}/decisao", headers=aluno, json={"preco": 100, "emprestimo": 80000})
    cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "ALTA_SELIC"})
    r = cliente.get(f"/api/aluno/empresas/{e}", headers=aluno).json()
    resultado = r["resultados"][0]
    assert resultado["divida_final"] == 50000  # limitado ao limite de crédito
    assert abs(resultado["dre"]["juros"] - 50000 * 0.03) < 1e-6  # 2,5% + 0,5 p.p.
    assert resultado["fase"] == "CAPTACAO"


def test_notificacao_fiscal_depende_do_networking(cliente, professor):
    turma = _criar_turma(cliente, professor)
    a1 = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    a2 = cadastrar(cliente, "Bia", "bia@aluno.iffar.edu.br")
    e1 = _entrar(cliente, a1, turma["codigo"], "Serial", classe="SERIAL")  # networking 35
    e2 = _entrar(cliente, a2, turma["codigo"], "Franquia", classe="FRANQUIA")  # networking 20
    cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "NOTIFICACAO_FISCAL"})
    m1 = cliente.get(f"/api/aluno/empresas/{e1}", headers=a1).json()["resultados"][0]["dre"]["multas"]
    m2 = cliente.get(f"/api/aluno/empresas/{e2}", headers=a2).json()["resultados"][0]["dre"]
    assert m1 == 0
    assert m2["multas"] == 3500
    assert m2["royalties"] > 0  # franquia paga royalties


def test_porter_meio_termo(cliente, professor):
    turma = _criar_turma(cliente, professor)
    aluno = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    e = _entrar(cliente, aluno, turma["codigo"], "Ana")
    cliente.put(f"/api/aluno/empresas/{e}/decisao", headers=aluno, json={"preco": 80, "marketing": 3000, "pd": 2000})
    cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "NENHUM"})
    alertas = cliente.get(f"/api/aluno/empresas/{e}", headers=aluno).json()["resultados"][0]["alertas"]
    assert any("meio-termo" in a for a in alertas)


def test_aluno_nao_entra_depois_do_inicio(cliente, professor):
    turma = _criar_turma(cliente, professor)
    a1 = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    _entrar(cliente, a1, turma["codigo"], "Ana")
    cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "NENHUM"})
    a2 = cadastrar(cliente, "Bia", "bia@aluno.iffar.edu.br")
    r = cliente.post(
        "/api/aluno/turmas/entrar",
        headers=a2,
        json={"codigo": turma["codigo"], "nome_empresa": "Bia", "tipo_entrada_gem": "NECESSIDADE", "classe_dornelas": "SOCIAL"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Tributos
# ---------------------------------------------------------------------------
def test_aliquotas_do_simples_anexo_i():
    assert abs(aliquota_efetiva_simples(100_000) - 0.04) < 1e-9
    # 2ª faixa: (300.000 × 7,3% − 5.940) / 300.000 = 5,32%
    assert abs(aliquota_efetiva_simples(300_000) - 0.0532) < 1e-9
    assert rbt12([10_000] * 3) == 120_000
    assert rbt12([10_000] * 15) == 120_000


def test_lucro_presumido():
    imposto, aliquota = calcular_imposto(RegimeTributario.LUCRO_PRESUMIDO, 10_000, 4_000, [], 81, 0.17)
    assert abs(imposto - (10_000 * 0.0593 + 6_000 * 0.17)) < 1e-6


def test_simulacao_longa_estavel(cliente, professor):
    """Doze rodadas com decisões aleatórias não podem gerar erro nem valores inválidos."""
    turma = _criar_turma(cliente, professor, total_rodadas=12)
    rng = random.Random(42)
    alunos = []
    for i in range(5):
        cab = cadastrar(cliente, f"Aluno {i}", f"a{i}@aluno.iffar.edu.br")
        alunos.append((cab, _entrar(cliente, cab, turma["codigo"], f"Empresa {i}", regime=rng.choice(["MEI", "SIMPLES_NACIONAL", "LUCRO_PRESUMIDO"]))))
    for _ in range(12):
        for cab, e in alunos:
            painel = cliente.get(f"/api/aluno/empresas/{e}", headers=cab).json()
            cliente.put(
                f"/api/aluno/empresas/{e}/decisao",
                headers=cab,
                json={
                    "preco": rng.uniform(60, 160),
                    "marketing": rng.choice([0, 500, 2000, 5000]),
                    "pd": rng.choice([0, 1000, 3000]),
                    "networking": rng.choice([0, 300]),
                    "contratar": rng.choice([0, 0, 1]),
                    "demitir": 1 if painel["empresa"]["funcionarios"] > 2 and rng.random() < 0.3 else 0,
                    "emprestimo": rng.choice([0, 0, 10000]),
                },
            )
        r = cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "SORTEAR"})
        assert r.status_code == 200, r.text
    final = cliente.get(f"/api/professor/turmas/{turma['id']}", headers=professor).json()
    assert final["turma"]["status"] == "ENCERRADA"
    for linha in final["ranking"]:
        assert linha["patrimonio"] == linha["patrimonio"]  # não é NaN
