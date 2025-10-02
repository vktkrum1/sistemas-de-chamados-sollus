"""merge user_id branches

Revision ID: 8d2b24ac7d03
Revises: a1b2c3d4e5f6, 9f1a_unify_user_id
Create Date: 2025-09-11 11:04:18.120972

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d2b24ac7d03'
down_revision = ('a1b2c3d4e5f6', '9f1a_unify_user_id')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
