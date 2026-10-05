"""Adota a estrutura inicial sem recriar tabelas ou apagar o histórico.

Snapshot congelado: futuras mudanças de app.models exigem novas revisões.
As duas colunas posteriores de usuários ficam nas revisões seguintes.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_base"
down_revision = None
branch_labels = None
depends_on = None


def _esquema_inicial():
    metadata = sa.MetaData()
    sa.Table(
        'usuarios', metadata,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=200), nullable=False),
        sa.Column('senha_hash', sa.String(length=300), nullable=False),
        sa.Column('papel', sa.Enum('ALUNO', 'PROFESSOR', name='papel'), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    sa.Index('ix_usuarios_email', metadata.tables['usuarios'].c['email'], unique=True)
    sa.Table(
        'tokens_recuperacao', metadata,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expira_em', sa.DateTime(), nullable=False),
        sa.Column('usado_em', sa.DateTime(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    sa.Index('ix_tokens_recuperacao_token_hash', metadata.tables['tokens_recuperacao'].c['token_hash'], unique=True)
    sa.Index('ix_tokens_recuperacao_usuario_id', metadata.tables['tokens_recuperacao'].c['usuario_id'], unique=False)
    sa.Table(
        'turmas', metadata,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('codigo', sa.String(length=12), nullable=False),
        sa.Column('professor_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('ABERTA', 'ENCERRADA', name='statusturma'), nullable=False),
        sa.Column('rodada_atual', sa.Integer(), nullable=False),
        sa.Column('total_rodadas', sa.Integer(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.Column('caixa_inicial', sa.Float(), nullable=False),
        sa.Column('preco_referencia', sa.Float(), nullable=False),
        sa.Column('custo_unitario', sa.Float(), nullable=False),
        sa.Column('demanda_base_por_empresa', sa.Float(), nullable=False),
        sa.Column('crescimento_mercado_mensal', sa.Float(), nullable=False),
        sa.Column('produtividade_por_pessoa', sa.Float(), nullable=False),
        sa.Column('custos_fixos_mensais', sa.Float(), nullable=False),
        sa.Column('salario_base', sa.Float(), nullable=False),
        sa.Column('taxa_juros_mensal', sa.Float(), nullable=False),
        sa.Column('taxa_cheque_especial', sa.Float(), nullable=False),
        sa.Column('limite_credito', sa.Float(), nullable=False),
        sa.Column('probabilidade_evento', sa.Float(), nullable=False),
        sa.Column('teto_mei_anual', sa.Float(), nullable=False),
        sa.Column('das_mei_mensal', sa.Float(), nullable=False),
        sa.Column('aliquota_icms', sa.Float(), nullable=False),
        sa.Column('cmv_multiplicador', sa.Float(), nullable=False),
        sa.Column('cmv_rodadas_restantes', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['professor_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    sa.Index('ix_turmas_codigo', metadata.tables['turmas'].c['codigo'], unique=True)
    sa.Table(
        'empresas', metadata,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('turma_id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.Column('tipo_entrada_gem', sa.Enum('NECESSIDADE', 'OPORTUNIDADE', name='tipoentradagem'), nullable=False),
        sa.Column('classe_dornelas', sa.Enum('SERIAL', 'FRANQUIA', 'CORPORATIVO', 'SOCIAL', name='classedornelas'), nullable=False),
        sa.Column('autoeficacia', sa.Float(), nullable=False),
        sa.Column('necessidade_realizacao', sa.Float(), nullable=False),
        sa.Column('networking', sa.Float(), nullable=False),
        sa.Column('fase_atual', sa.Enum('IDEACAO', 'PLANEJAMENTO', 'CAPTACAO', 'OPERACAO_ESTAVEL', 'SOBREVIVENCIA', name='faseatual'), nullable=False),
        sa.Column('regime_tributario', sa.Enum('MEI', 'SIMPLES_NACIONAL', 'LUCRO_PRESUMIDO', name='regimetributario'), nullable=False),
        sa.Column('regime_pretendido', sa.Enum('MEI', 'SIMPLES_NACIONAL', 'LUCRO_PRESUMIDO', name='regimetributario'), nullable=True),
        sa.Column('caixa', sa.Float(), nullable=False),
        sa.Column('divida', sa.Float(), nullable=False),
        sa.Column('funcionarios', sa.Integer(), nullable=False),
        sa.Column('marca', sa.Float(), nullable=False),
        sa.Column('qualidade', sa.Float(), nullable=False),
        sa.Column('faturamento_ano', sa.Float(), nullable=False),
        sa.Column('das_mei_pago_ano', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['aluno_id'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['turma_id'], ['turmas.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('turma_id', 'aluno_id', name='uq_empresa_turma_aluno')
    )
    sa.Index('ix_empresas_aluno_id', metadata.tables['empresas'].c['aluno_id'], unique=False)
    sa.Index('ix_empresas_turma_id', metadata.tables['empresas'].c['turma_id'], unique=False)
    sa.Table(
        'eventos_rodada', metadata,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('turma_id', sa.Integer(), nullable=False),
        sa.Column('rodada', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(length=40), nullable=False),
        sa.Column('titulo', sa.String(length=120), nullable=False),
        sa.Column('narrativa', sa.String(length=1000), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['turma_id'], ['turmas.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('turma_id', 'rodada', name='uq_evento_turma_rodada')
    )
    sa.Index('ix_eventos_rodada_turma_id', metadata.tables['eventos_rodada'].c['turma_id'], unique=False)
    sa.Table(
        'decisoes', metadata,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('rodada', sa.Integer(), nullable=False),
        sa.Column('preco', sa.Float(), nullable=False),
        sa.Column('marketing', sa.Float(), nullable=False),
        sa.Column('pd', sa.Float(), nullable=False),
        sa.Column('networking', sa.Float(), nullable=False),
        sa.Column('contratar', sa.Integer(), nullable=False),
        sa.Column('demitir', sa.Integer(), nullable=False),
        sa.Column('emprestimo', sa.Float(), nullable=False),
        sa.Column('amortizacao', sa.Float(), nullable=False),
        sa.Column('regime_solicitado', sa.Enum('MEI', 'SIMPLES_NACIONAL', 'LUCRO_PRESUMIDO', name='regimetributario'), nullable=True),
        sa.Column('automatica', sa.Integer(), nullable=False),
        sa.Column('enviada_em', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'rodada', name='uq_decisao_empresa_rodada')
    )
    sa.Index('ix_decisoes_empresa_id', metadata.tables['decisoes'].c['empresa_id'], unique=False)
    sa.Table(
        'resultados', metadata,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empresa_id', sa.Integer(), nullable=False),
        sa.Column('rodada', sa.Integer(), nullable=False),
        sa.Column('preco', sa.Float(), nullable=False),
        sa.Column('demanda', sa.Float(), nullable=False),
        sa.Column('capacidade', sa.Float(), nullable=False),
        sa.Column('unidades_vendidas', sa.Float(), nullable=False),
        sa.Column('participacao_mercado', sa.Float(), nullable=False),
        sa.Column('receita', sa.Float(), nullable=False),
        sa.Column('impostos', sa.Float(), nullable=False),
        sa.Column('cmv', sa.Float(), nullable=False),
        sa.Column('folha', sa.Float(), nullable=False),
        sa.Column('custos_fixos', sa.Float(), nullable=False),
        sa.Column('marketing', sa.Float(), nullable=False),
        sa.Column('pd', sa.Float(), nullable=False),
        sa.Column('networking_invest', sa.Float(), nullable=False),
        sa.Column('rescisoes', sa.Float(), nullable=False),
        sa.Column('royalties', sa.Float(), nullable=False),
        sa.Column('juros', sa.Float(), nullable=False),
        sa.Column('multas', sa.Float(), nullable=False),
        sa.Column('lucro_liquido', sa.Float(), nullable=False),
        sa.Column('caixa_final', sa.Float(), nullable=False),
        sa.Column('divida_final', sa.Float(), nullable=False),
        sa.Column('regime', sa.Enum('MEI', 'SIMPLES_NACIONAL', 'LUCRO_PRESUMIDO', name='regimetributario'), nullable=False),
        sa.Column('aliquota_efetiva', sa.Float(), nullable=False),
        sa.Column('funcionarios', sa.Integer(), nullable=False),
        sa.Column('marca', sa.Float(), nullable=False),
        sa.Column('qualidade', sa.Float(), nullable=False),
        sa.Column('autoeficacia', sa.Float(), nullable=False),
        sa.Column('networking', sa.Float(), nullable=False),
        sa.Column('necessidade_realizacao', sa.Float(), nullable=False),
        sa.Column('fase', sa.Enum('IDEACAO', 'PLANEJAMENTO', 'CAPTACAO', 'OPERACAO_ESTAVEL', 'SOBREVIVENCIA', name='faseatual'), nullable=False),
        sa.Column('alertas', sa.JSON(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empresa_id', 'rodada', name='uq_resultado_empresa_rodada')
    )
    sa.Index('ix_resultados_empresa_id', metadata.tables['resultados'].c['empresa_id'], unique=False)

    return metadata


def upgrade():
    conexao = op.get_bind()
    metadata = _esquema_inicial()
    inspetor = sa.inspect(conexao)
    # Apenas esquemas conhecidos são adotados. Uma tabela incompatível não
    # recebe uma versão que fingiria ter sido migrada com sucesso.
    for tabela in metadata.sorted_tables:
        if inspetor.has_table(tabela.name):
            existentes = {c["name"] for c in inspetor.get_columns(tabela.name)}
            ausentes = set(tabela.c.keys()) - existentes
            if ausentes:
                raise RuntimeError(
                    f"Banco incompatível: {tabela.name} sem as colunas "
                    f"{', '.join(sorted(ausentes))}. Revise o esquema antes de migrar."
                )
    # checkfirst também reutiliza os ENUMs compartilhados do PostgreSQL.
    metadata.create_all(bind=conexao, checkfirst=True)


def downgrade():
    raise RuntimeError(
        "A revisão inicial pode ter adotado tabelas com dados existentes; "
        "restaure um backup para voltar sem apagar o histórico."
    )
