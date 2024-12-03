"""unit_contact_email_non_nullable

Revision ID: e02fe8fde71e
Revises: 
Create Date: 2024-12-02 13:08:43.073488

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e02fe8fde71e"
down_revision = "3d610b382383"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        table_name="units",
        column_name="contact_email",
        existing_type=sa.String(length=255),
        server_default="delivery@scilifelab.se",
        nullable=False,
    )


def downgrade():
    op.alter_column(
        table_name="units",
        column_name="contact_email",
        existing_type=sa.String(length=255),
        nullable=True,
    )
