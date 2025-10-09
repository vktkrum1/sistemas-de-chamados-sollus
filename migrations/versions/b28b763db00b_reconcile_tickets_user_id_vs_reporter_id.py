from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# Ajuste: use o ID REAL da merge criada no passo 1:
revision = 'fix_tickets_user_reconcile'
down_revision = '8d2b24ac7d03'  # <-- SUBSTITUA pelo Revision ID da MERGE
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # --- 1) Garante coluna user_id e FK para users.id ---
    cols = {c['name'] for c in insp.get_columns('tickets')}
    if 'user_id' not in cols:
        op.add_column('tickets', sa.Column('user_id', sa.Integer(), nullable=True))
        try:
            op.create_foreign_key(
                'fk_tickets_user_id_users', 'tickets', 'users',
                ['user_id'], ['id'], ondelete='SET NULL'
            )
        except Exception:
            pass  # Se já existir com outro nome, ignoramos

    # --- 2) Se existir reporter_id, migra valores e remove FK + coluna ---
    if 'reporter_id' in cols:
        # Copia dados de reporter_id para user_id onde user_id estiver nulo
        try:
            bind.execute(text(
                "UPDATE tickets SET user_id = reporter_id "
                "WHERE user_id IS NULL AND reporter_id IS NOT NULL"
            ))
        except Exception:
            pass

        # Descobre e remove qualquer FK que referencie reporter_id
        fk_rows = bind.execute(text("""
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'tickets'
              AND COLUMN_NAME = 'reporter_id'
              AND REFERENCED_TABLE_NAME IS NOT NULL
        """)).fetchall()
        for (fk_name,) in fk_rows:
            try:
                op.drop_constraint(fk_name, 'tickets', type_='foreignkey')
            except Exception:
                pass

        # Finalmente, dropa a coluna reporter_id (se ainda existir)
        with op.batch_alter_table('tickets') as b:
            try:
                b.drop_column('reporter_id')
            except Exception:
                pass

    # --- 3) Torna user_id NOT NULL (opcional; comente se quiser permitir nulo) ---
    # Antes, garanta que não há linhas com user_id nulo, senão falha:
    try:
        bind.execute(text("""
            UPDATE tickets t
            SET user_id = (
                SELECT id FROM users ORDER BY id LIMIT 1
            )
            WHERE user_id IS NULL
        """))
    except Exception:
        pass

    # Agora altera para NOT NULL (se quiser manter nulo, comente este bloco)
    try:
        with op.batch_alter_table('tickets') as b:
            b.alter_column('user_id', existing_type=sa.Integer(), nullable=False)
    except Exception:
        # Se não conseguir (por haver nulos), mantenha como NULL e siga
        pass


def downgrade():
    # Sem downgrade (não reintroduz reporter_id)
    pass
