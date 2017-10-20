"""account uniqueness

Revision ID: d2f6a808a2b5
Revises: faf6d7094ae3
Create Date: 2017-10-21 00:35:16.442993

"""
from alembic import op
import sqlalchemy as sa
import kneipy_core


# revision identifiers, used by Alembic.
revision = 'd2f6a808a2b5'
down_revision = 'faf6d7094ae3'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
        ALTER TABLE account
        RENAME CONSTRAINT
            uq_account_balancesheet_id
        TO
            uq_account_balancesheet_id_for_fk;
    ''')
    op.create_unique_constraint('uq_account_balancesheet_id_name', 'account', ['balancesheet_id', 'name'])
    op.create_unique_constraint(op.f('uq_account_person_id'), 'account', ['person_id', 'balancesheet_id'])


def downgrade():
    op.drop_constraint(op.f('uq_account_person_id'), 'account', type_='unique')
    op.drop_constraint('uq_account_balancesheet_id_name', 'account', type_='unique')
    op.execute('''
        ALTER TABLE account
        RENAME CONSTRAINT
            uq_account_balancesheet_id_for_fk
        TO
            uq_account_balancesheet_id;
    ''')
