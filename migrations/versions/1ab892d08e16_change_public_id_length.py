"""change_public_id_length

Revision ID: 1ab892d08e16
Revises: 1fbd604872e9
Create Date: 2022-04-13 06:16:56.046361

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "1ab892d08e16"
down_revision = "1fbd604872e9"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "invites",
        "nonce",
        existing_type=mysql.TINYBLOB(),
        type_=sa.LargeBinary(length=12),
        existing_nullable=True,
    )
    op.alter_column(
        "projects",
        "public_key",
        existing_type=mysql.TINYBLOB(),
        type_=sa.LargeBinary(length=100),
        existing_nullable=True,
    )
    op.alter_column(
        "units",
        "public_id",
        existing_type=mysql.VARCHAR(length=255),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "hotp_secret",
        existing_type=mysql.TINYBLOB(),
        type_=sa.LargeBinary(length=20),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "kd_salt",
        existing_type=mysql.TINYBLOB(),
        type_=sa.LargeBinary(length=32),
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "nonce",
        existing_type=mysql.TINYBLOB(),
        type_=sa.LargeBinary(length=12),
        existing_nullable=True,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "users",
        "nonce",
        existing_type=sa.LargeBinary(length=12),
        type_=mysql.TINYBLOB(),
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "kd_salt",
        existing_type=sa.LargeBinary(length=32),
        type_=mysql.TINYBLOB(),
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "hotp_secret",
        existing_type=sa.LargeBinary(length=20),
        type_=mysql.TINYBLOB(),
        existing_nullable=False,
    )
    op.alter_column(
        "units",
        "public_id",
        existing_type=sa.String(length=50),
        type_=mysql.VARCHAR(length=255),
        existing_nullable=False,
    )
    op.alter_column(
        "projects",
        "public_key",
        existing_type=sa.LargeBinary(length=100),
        type_=mysql.TINYBLOB(),
        existing_nullable=True,
    )
    op.alter_column(
        "invites",
        "nonce",
        existing_type=sa.LargeBinary(length=12),
        type_=mysql.TINYBLOB(),
        existing_nullable=True,
    )
    # ### end Alembic commands ###