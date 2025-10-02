"""unify reporter_id -> user_id on tickets"""

from alembic import op
import sqlalchemy as sa

# revise identifiers
revision = '9f1a_unify_user_id'
down_revision = '732b4644c400'  # ajuste se seu head anterior for outro
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Lista de colunas atuais da tabela tickets
    cols = [r[0] for r in conn.execute(sa.text(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME='tickets' AND TABLE_SCHEMA=DATABASE()"
    )).fetchall()]

    has_user = 'user_id' in cols
    has_reporter = 'reporter_id' in cols

    # Se só existe reporter_id, criamos user_id e copiamos os dados
    if has_reporter and not has_user:
        op.add_column('tickets', sa.Column('user_id', sa.Integer(), nullable=True))
        conn.execute(sa.text("UPDATE tickets SET user_id = reporter_id WHERE user_id IS NULL"))

    # Se existem as duas, só garantimos que user_id está preenchido
    if has_user and has_reporter:
        conn.execute(sa.text("UPDATE tickets SET user_id = COALESCE(user_id, reporter_id)"))

    # Remover FK antiga em reporter_id (se existir)
    if has_reporter:
        # Descobre o nome da FK em reporter_id
        fk_names = [r[0] for r in conn.execute(sa.text(
            "SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
            "WHERE TABLE_NAME='tickets' AND TABLE_SCHEMA=DATABASE() AND COLUMN_NAME='reporter_id' "
            "AND REFERENCED_TABLE_NAME IS NOT NULL"
        )).fetchall()]
        for fk in fk_names:
            try:
                conn.execute(sa.text(f"ALTER TABLE tickets DROP FOREIGN KEY `{fk}`"))
            except Exception:
                pass

        # Por fim, remove a coluna reporter_id
        op.drop_column('tickets', 'reporter_id')

    # Garante FK correta em user_id → users(id)
    # Primeiro, apaga FK antiga se tiver
    fk_user = [r[0] for r in conn.execute(sa.text(
        "SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
        "WHERE TABLE_NAME='tickets' AND TABLE_SCHEMA=DATABASE() AND COLUMN_NAME='user_id' "
        "AND REFERENCED_TABLE_NAME IS NOT NULL"
    )).fetchall()]
    for fk in fk_user:
        try:
            conn.execute(sa.text(f"ALTER TABLE tickets DROP FOREIGN KEY `{fk}`"))
        except Exception:
            pass

    # Cria FK padrão (permite NULL para não travar histórico)
    conn.execute(sa.text(
        "ALTER TABLE tickets "
        "ADD CONSTRAINT fk_tickets_user_id FOREIGN KEY (user_id) "
        "REFERENCES users (id) ON DELETE SET NULL"
    ))


def downgrade():
    # (opcional) recria reporter_id vazio e derruba FK de user_id
    conn = op.get_bind()
    # drop FK user_id
    fk_user = [r[0] for r in conn.execute(sa.text(
        "SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
        "WHERE TABLE_NAME='tickets' AND TABLE_SCHEMA=DATABASE() AND COLUMN_NAME='user_id' "
        "AND REFERENCED_TABLE_NAME IS NOT NULL"
    )).fetchall()]
    for fk in fk_user:
        try:
            conn.execute(sa.text(f"ALTER TABLE tickets DROP FOREIGN KEY `{fk}`"))
        except Exception:
            pass

    op.add_column('tickets', sa.Column('reporter_id', sa.Integer(), nullable=True))
    # não copiamos de volta (downgrade best-effort)
