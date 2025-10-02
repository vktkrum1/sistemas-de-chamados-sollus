from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '473afb208984'
down_revision = 'fix_tickets_user_reconcile'
branch_labels = None
depends_on = None

def _has_table(bind, name: str) -> bool:
    insp = inspect(bind)
    return name in insp.get_table_names()

def upgrade():
    bind = op.get_bind()

    # tasks
    if not _has_table(bind, 'tasks'):
        op.create_table(
            'tasks',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('position', sa.Integer(), nullable=False),
            sa.Column('due_date', sa.Date(), nullable=True),
            sa.Column('assignee_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            mysql_engine='InnoDB',
            mysql_charset='utf8mb4',
        )

    # task_logs
    if not _has_table(bind, 'task_logs'):
        op.create_table(
            'task_logs',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column('task_id', sa.Integer(), sa.ForeignKey('tasks.id'), nullable=False),
            sa.Column('log_date', sa.Date(), nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            mysql_engine='InnoDB',
            mysql_charset='utf8mb4',
        )
        op.create_index('ix_task_logs_task_id', 'task_logs', ['task_id'])

def downgrade():
    # safe drop
    bind = op.get_bind()
    insp = inspect(bind)

    if 'task_logs' in insp.get_table_names():
        op.drop_index('ix_task_logs_task_id', table_name='task_logs')
        op.drop_table('task_logs')

    if 'tasks' in insp.get_table_names():
        op.drop_table('tasks')
