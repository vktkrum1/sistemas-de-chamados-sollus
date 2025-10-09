"""add author_id to task_logs"""

from alembic import op
import sqlalchemy as sa

revision = 'dadd51eb9a31'
down_revision = '7de17f16cdde'   # << ESTE É O ID REAL ANTERIOR
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('task_logs') as batch_op:
        batch_op.add_column(sa.Column('author_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_task_logs_author', ['author_id'])
        batch_op.create_foreign_key(
            'fk_task_logs_author', 'users',
            ['author_id'], ['id'],
            ondelete='SET NULL'
        )

def downgrade():
    with op.batch_alter_table('task_logs') as batch_op:
        try:
            batch_op.drop_constraint('fk_task_logs_author', type_='foreignkey')
        except Exception:
            pass
        try:
            batch_op.drop_index('ix_task_logs_author')
        except Exception:
            pass
        batch_op.drop_column('author_id')
