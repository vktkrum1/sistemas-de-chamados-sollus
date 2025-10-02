"""attachments

Revision ID: 732b4644c400
Revises: 99d8a93c158f
Create Date: 2025-09-10 15:30:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '732b4644c400'
down_revision = '99d8a93c158f'
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

    # 1) Criar a tabela se não existir
    if not _has_table(bind, "attachments"):
        op.create_table(
            'attachments',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('ticket_id', sa.Integer, sa.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False),
            sa.Column('filename', sa.String(255), nullable=False),
            sa.Column('stored_name', sa.String(255), nullable=False),
            sa.Column('content_type', sa.String(120)),
            sa.Column('size', sa.Integer),
            sa.Column('uploaded_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('uploaded_by', sa.Integer, sa.ForeignKey('users.id')),
            mysql_engine='InnoDB',
            mysql_charset='utf8mb4'
        )
        # Se quiser índice explícito: op.create_index('ix_attachments_ticket_id', 'attachments', ['ticket_id'])
        return  # tabela criada do zero, terminou

    # 2) Se já existe, adicionar o que falta (colunas/FKs)
    cols = _columns(bind, "attachments")

    # filename
    if 'filename' not in cols:
        op.add_column('attachments', sa.Column('filename', sa.String(255), nullable=False, server_default=''))
        op.alter_column('attachments', 'filename', server_default=None)

    # stored_name
    if 'stored_name' not in cols:
        op.add_column('attachments', sa.Column('stored_name', sa.String(255), nullable=False, server_default=''))
        op.alter_column('attachments', 'stored_name', server_default=None)

    # content_type
    if 'content_type' not in cols:
        op.add_column('attachments', sa.Column('content_type', sa.String(120), nullable=True))

    # size
    if 'size' not in cols:
        op.add_column('attachments', sa.Column('size', sa.Integer(), nullable=True))

    # uploaded_at
    if 'uploaded_at' not in cols:
        op.add_column('attachments', sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))

    # uploaded_by
    need_uploaded_by_fk = False
    if 'uploaded_by' not in cols:
        op.add_column('attachments', sa.Column('uploaded_by', sa.Integer(), nullable=True))
        need_uploaded_by_fk = True

    # Garantir FK ticket_id -> tickets.id (CASCADE) caso não tenha sido criada automaticamente
    if not _fk_exists_exact(bind, 'attachments', 'tickets', ['ticket_id']):
        op.create_foreign_key(
            'fk_attachments_ticket_id',
            'attachments', 'tickets',
            ['ticket_id'], ['id'],
            ondelete='CASCADE'
        )

    # Garantir FK uploaded_by -> users.id
    if need_uploaded_by_fk or not _fk_exists_exact(bind, 'attachments', 'users', ['uploaded_by']):
        # Pode falhar se não existir tabela users; no teu projeto existe.
        op.create_foreign_key(
            'fk_attachments_uploaded_by',
            'attachments', 'users',
            ['uploaded_by'], ['id']
        )


def downgrade():
    bind = op.get_bind()
    if _has_table(bind, "attachments"):
        # Se você criou índices/FKs nomeados acima, drope-os aqui primeiro se necessário
        op.drop_table('attachments')
