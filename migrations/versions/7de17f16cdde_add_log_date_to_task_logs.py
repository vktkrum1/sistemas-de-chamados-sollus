"""add log_date to task_logs"""

from alembic import op
import sqlalchemy as sa

revision = '7de17f16cdde'
down_revision = '473afb208984'   # << de acordo com o history
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("task_logs") as batch_op:
        batch_op.add_column(sa.Column("log_date", sa.Date(), nullable=True))

    # backfill: usa a data do created_at
    op.execute("UPDATE task_logs SET log_date = DATE(created_at) WHERE log_date IS NULL")

    # opcional: índice combinado (melhora buscas por tarefa+data)
    with op.batch_alter_table("task_logs") as batch_op:
        batch_op.create_index("ix_task_logs_task_date", ["task_id", "log_date"])

    # trava como NOT NULL após popular
    with op.batch_alter_table("task_logs") as batch_op:
        batch_op.alter_column("log_date", existing_type=sa.Date(), nullable=False)

def downgrade():
    with op.batch_alter_table("task_logs") as batch_op:
        batch_op.drop_index("ix_task_logs_task_date")
        batch_op.drop_column("log_date")
