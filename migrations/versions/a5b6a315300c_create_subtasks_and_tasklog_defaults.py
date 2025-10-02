"""create subtasks and tasklog defaults

Revision ID: a5b6a315300c
Revises: dadd51eb9a31
Create Date: 2025-09-19 16:22:35.908356

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'a5b6a315300c'
down_revision = 'dadd51eb9a31'
branch_labels = None
depends_on = None


from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a5b6a315300c'
down_revision = 'dadd51eb9a31'
branch_labels = None
depends_on = None


def upgrade():
    # --- 1) criar tabela SUBTASKS ---
    op.create_table(
        'subtasks',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('task_id', sa.Integer(), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('work_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('assignee_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    op.create_index('ix_subtasks_task_id', 'subtasks', ['task_id'])
    op.create_index('ix_subtasks_assignee_id', 'subtasks', ['assignee_id'])

    # --- 2) garantir log_date em TASK_LOGS sem nulos e com default ---
    # Preenche linhas antigas que porventura estejam NULL
    op.execute("UPDATE task_logs SET log_date = CURDATE() WHERE log_date IS NULL")

    # Define NOT NULL e default no servidor para novas linhas
    op.alter_column(
        'task_logs', 'log_date',
        existing_type=sa.Date(),
        nullable=False,
        server_default=sa.text('CURRENT_DATE')
    )

    # Opcional: created_at também NOT NULL
    op.alter_column(
        'task_logs', 'created_at',
        existing_type=sa.DateTime(),
        nullable=False,
        existing_server_default=None,
        server_default=sa.text('CURRENT_TIMESTAMP')
    )


def downgrade():
    # reverte alterações
    op.drop_index('ix_subtasks_assignee_id', table_name='subtasks')
    op.drop_index('ix_subtasks_task_id', table_name='subtasks')
    op.drop_table('subtasks')

    # tira o default de log_date (volta a coluna como era antes; mantém NOT NULL por segurança)
    op.alter_column(
        'task_logs', 'log_date',
        existing_type=sa.Date(),
        nullable=False,
        server_default=None
    )

    # tira default de created_at também
    op.alter_column(
        'task_logs', 'created_at',
        existing_type=sa.DateTime(),
        nullable=False,
        server_default=None
    )
