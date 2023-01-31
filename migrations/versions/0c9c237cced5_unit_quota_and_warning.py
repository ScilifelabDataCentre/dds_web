"""unit_quota_and_warning

Revision ID: 0c9c237cced5
Revises: eb395af90e18
Create Date: 2023-01-10 14:30:57.089391

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "0c9c237cced5"
down_revision = "eb395af90e18"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # Add new columns
    op.add_column("units", sa.Column("quota", sa.BigInteger(), nullable=False))
    op.add_column("units", sa.Column("warning_level", sa.Float(), nullable=False, default=0.80))

    # Update existing columns
    # 1. Load table - need to load columns in order to use
    unit_table = sa.sql.table(
        "units", sa.sql.column("quota", mysql.BIGINT), sa.sql.column("warning_level", mysql.FLOAT)
    )
    # 2. Update column value - set value to 100 TB
    op.execute(unit_table.update().values(quota=100 * (10**12)))
    # 3. Update column value - set value to 0.80
    op.execute(unit_table.update().values(warning_level=0.8))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("units", "warning_level")
    op.drop_column("units", "quota")
    # ### end Alembic commands ###
