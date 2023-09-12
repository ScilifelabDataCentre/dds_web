"""set-sto2-to-nullable

Revision ID: f27c5988d640
Revises: 1e56b6212479
Create Date: 2023-09-07 09:36:25.289025

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "f27c5988d640"
down_revision = "1e56b6212479"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "units", "sto2_endpoint", existing_type=mysql.VARCHAR(length=255), nullable=True
    )
    op.alter_column("units", "sto2_name", existing_type=mysql.VARCHAR(length=255), nullable=True)
    op.alter_column("units", "sto2_access", existing_type=mysql.VARCHAR(length=255), nullable=True)
    op.alter_column("units", "sto2_secret", existing_type=mysql.VARCHAR(length=255), nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("units", "sto2_secret", existing_type=mysql.VARCHAR(length=255), nullable=False)
    op.alter_column("units", "sto2_access", existing_type=mysql.VARCHAR(length=255), nullable=False)
    op.alter_column("units", "sto2_name", existing_type=mysql.VARCHAR(length=255), nullable=False)
    op.alter_column(
        "units", "sto2_endpoint", existing_type=mysql.VARCHAR(length=255), nullable=False
    )
    # ### end Alembic commands ###
