"""add_totp

Revision ID: ee441d642d7a
Revises: 1256117ad629
Create Date: 2022-03-31 19:37:39.689841

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'ee441d642d7a'
down_revision = '1256117ad629'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('totp_enabled', mysql.TINYINT(display_width=1), nullable=True))
    op.add_column('users', sa.Column('_totp_secret', sa.LargeBinary(length=64), nullable=True))
    op.add_column('users', sa.Column('totp_last_verified', sa.DateTime(), nullable=True))

    # Fill in default value for totp_enabled
    user_table = sa.sql.table(
        'users',
        sa.sql.column('totp_enabled', mysql.TINYINT(display_width=1)),
    )
    op.execute(user_table.update().values(totp_enabled=False))

    # Make totp_enabled not nullable
    op.alter_column('users', 'totp_enabled', existing_type=mysql.TINYINT(display_width=1), nullable=False)


def downgrade():
    op.drop_column('users', 'totp_last_verified')
    op.drop_column('users', '_totp_secret')
    op.drop_column('users', 'totp_enabled')
    # ### end Alembic commands ###
