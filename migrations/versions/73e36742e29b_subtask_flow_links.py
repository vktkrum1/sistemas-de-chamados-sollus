"""subtask flow links

Revision ID: 73e36742e29b
Revises: a5b6a315300c
Create Date: 2025-09-22
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "73e36742e29b"
down_revision = "a5b6a315300c"
branch_labels = None
depends_on = None


def _table_exists(insp, name: str) -> bool:
    try:
        return name in insp.get_table_names()
    except Exception:
        return False


def _index_exists(insp, table: str, index_name: str) -> bool:
    try:
        return any(i.get("name") == index_name for i in insp.get_indexes(table))
    except Exception:
        return False


def _uq_exists(insp, table: str, uq_name: str) -> bool:
    try:
        return any(u.get("name") == uq_name for u in insp.get_unique_constraints(table))
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    tbl = "subtask_links"
    idx_task = "ix_subtask_links_task_id"
    uq_name = "uq_subtask_link"

    # cria a tabela só se NÃO existir
    if not _table_exists(insp, tbl):
        op.create_table(
            tbl,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("task_id", sa.Integer(), nullable=False),
            sa.Column("from_id", sa.Integer(), nullable=False),
            sa.Column("to_id", sa.Integer(), nullable=False),
            sa.Column("label", sa.String(length=80), nullable=True),
            sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["from_id"], ["subtasks.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["to_id"], ["subtasks.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("task_id", "from_id", "to_id", name=uq_name),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    # garante índice em task_id
    if _table_exists(insp, tbl) and not _index_exists(insp, tbl, idx_task):
        op.create_index(idx_task, tbl, ["task_id"], unique=False)

    # garante UNIQUE (task_id, from_id, to_id)
    if _table_exists(insp, tbl) and not _uq_exists(insp, tbl, uq_name):
        op.create_unique_constraint(uq_name, tbl, ["task_id", "from_id", "to_id"])


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    tbl = "subtask_links"
    idx_task = "ix_subtask_links_task_id"

    if _table_exists(insp, tbl):
        if _index_exists(insp, tbl, idx_task):
            op.drop_index(idx_task, table_name=tbl)
        op.drop_table(tbl)
