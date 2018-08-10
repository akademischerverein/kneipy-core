"""use numeric

Revision ID: 7f59a09fb3b0
Revises: a50ae13b7b40
Create Date: 2018-08-11 00:57:44.498940

"""
from alembic import op
import sqlalchemy as sa
import kneipy_core


# revision identifiers, used by Alembic.
revision = '7f59a09fb3b0'
down_revision = 'a50ae13b7b40'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'transaction', 'amount',
        existing_type=sa.BigInteger,
        type_=sa.Numeric(20, 5)
    )


def downgrade():
    op.alter_column(
        'transaction', 'amount',
        type_=sa.BigInteger,
        existing_type=sa.Numeric(20, 5)
    )
