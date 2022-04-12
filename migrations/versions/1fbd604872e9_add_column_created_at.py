"""add_column_created_at

Revision ID: 1fbd604872e9
Revises: 19b877061c98
Create Date: 2022-04-08 14:32:26.800385

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from dds_web.utils import current_time

# revision identifiers, used by Alembic.
revision = "1fbd604872e9"
down_revision = "19b877061c98"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "invites", sa.Column("created_at", sa.DateTime(), nullable=False, default=current_time())
    )


def downgrade():
    op.drop_column("invites", "created_at")
