"""add_totp

Revision ID: b01fc48f5939
Revises: 1ab892d08e16
Create Date: 2022-04-13 14:27:49.319000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "b01fc48f5939"
down_revision = "1ab892d08e16"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), nullable=False))
    op.add_column("users", sa.Column("_totp_secret", sa.LargeBinary(length=64), nullable=True))
    op.add_column("users", sa.Column("totp_last_verified", sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "totp_last_verified")
    op.drop_column("users", "_totp_secret")
    op.drop_column("users", "totp_enabled")
    # ### end Alembic commands ###