"""add user_id to tickets

Revision ID: a1b2c3d4e5f6
Revises: 732b4644c400
Create Date: 2025-09-10 17:20:00
"""
from alembic import op
import sqlalchemy as sa

# Substitua pelo ID real, se gerou via CLI
revision = 'a1b2c3d4e5f6'
down_revision = '732b4644c400'
branch_labels = None
depends_on = None


def _insp(bind):
    return sa.inspect(bind)


def _has_table(bind, name: str) -> bool:
    return _insp(bind).has_table(name)


def _columns(bind, table: str) -> set[str]:
    return {c["name"] for c in _insp(bind).get_columns(table)}


def _fk_exists_exact(bind, table: str, referred_table: str, local_cols: list[str]) -> bool:
    insp = _insp(bind)
    for fk in insp.get_foreign_keys(table):
        if fk.get("referred_table") == referred_table and fk.get("constrained_columns") == local_cols:
            return True
    return False


def upgrade():
    bind = op.get_bind()
    if not _has_table(bind, "tickets"):
        raise RuntimeError("Tabela 'tickets' não encontrada.")

    cols = _columns(bind, "tickets")

    # 1) Cria a coluna user_id se não existir (nullable=True para não falhar em dados antigos)
    if 'user_id' not in cols:
        op.add_column('tickets', sa.Column('user_id', sa.Integer(), nullable=True))
        # Índice opcional para performance
        op.create_index('ix_tickets_user_id', 'tickets', ['user_id'], unique=False)

    # 2) Garante a FK para users(id)
    if not _fk_exists_exact(bind, 'tickets', 'users', ['user_id']):
        op.create_foreign_key(
            'fk_tickets_user_id',
            'tickets', 'users',
            ['user_id'], ['id'],
            ondelete=None  # ajuste se quiser CASCADE em deleção de usuário
        )

    # (Opcional) Se quiser forçar NOT NULL, faça uma migração posterior depois de popular os dados antigos.


def downgrade():
    bind = op.get_bind()
    # Remover FK e índice antes da coluna
    try:
        op.drop_constraint('fk_tickets_user_id', 'tickets', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_index('ix_tickets_user_id', table_name='tickets')
    except Exception:
        pass
    # E por último a coluna
    try:
        op.drop_column('tickets', 'user_id')
    except Exception:
        pass
