"""drop ck_account_parent_type_check

Revision ID: 5b8118586860
Revises: 04c4aa99f54b
Create Date: 2018-07-08 13:36:58.021124

"""
from alembic import op
import sqlalchemy as sa
import kneipy_core


# revision identifiers, used by Alembic.
revision = '5b8118586860'
down_revision = '04c4aa99f54b'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        'ck_account_parent_type_check',
        'account'
    )


def downgrade():
    op.create_check_constraint(
        op.f('ck_account_parent_type_check'),
        'account',
        """
        (
            type = parent_type AND type IS NOT NULL
        ) OR (
            type NOT IN ('Profits', 'Expenses') AND parent_type IS NULL
        ) OR (
            type IN ('Profits', 'Expenses') AND parent_type = 'Capital'
        )
        """
    )
