"""fks transaction to account include balancesheet_id

Revision ID: d4dc4fe42010
Revises: ae1f9f33b46c
Create Date: 2017-10-17 13:49:48.216852

"""
from alembic import op
import sqlalchemy as sa
import kneipy_core


# revision identifiers, used by Alembic.
revision = 'd4dc4fe42010'
down_revision = 'ae1f9f33b46c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(op.f('uq_account_balancesheet_id'), 'account', ['balancesheet_id', 'id'])
    op.create_foreign_key('credit_account', 'transaction', 'account', ['credit_account_id', 'balancesheet_id'], ['id', 'balancesheet_id'], onupdate='RESTRICT', ondelete='RESTRICT')
    op.create_foreign_key('debit_account', 'transaction', 'account', ['debit_account_id', 'balancesheet_id'], ['id', 'balancesheet_id'], onupdate='RESTRICT', ondelete='RESTRICT')
    op.drop_constraint('fk_transaction_credit_account_id_account', 'transaction', type_='foreignkey')
    op.drop_constraint('fk_transaction_debit_account_id_account', 'transaction', type_='foreignkey')
    op.create_unique_constraint(op.f('uq_transaction_cancellation_for_transaction_id'), 'transaction', ['cancellation_for_transaction_id'])


def downgrade():
    op.create_foreign_key('fk_transaction_debit_account_id_account', 'transaction', 'account', ['debit_account_id'], ['id'], onupdate='RESTRICT', ondelete='RESTRICT')
    op.create_foreign_key('fk_transaction_credit_account_id_account', 'transaction', 'account', ['credit_account_id'], ['id'], onupdate='RESTRICT', ondelete='RESTRICT')
    op.drop_constraint('debit_account', 'transaction', type_='foreignkey')
    op.drop_constraint('credit_account', 'transaction', type_='foreignkey')
    op.drop_constraint(op.f('uq_account_balancesheet_id'), 'account', type_='unique')
    op.drop_constraint(op.f('uq_transaction_cancellation_for_transaction_id'), 'transaction', type_='unique')
