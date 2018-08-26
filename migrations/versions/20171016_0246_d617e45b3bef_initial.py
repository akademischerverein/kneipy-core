"""initial

Revision ID: d617e45b3bef
Revises:
Create Date: 2017-10-16 02:48:50.548457

"""
from alembic import op
import sqlalchemy as sa
import kneipy_core
from sqlalchemy.dialects import postgresql
from sqlalchemy import FetchedValue
# revision identifiers, used by Alembic.
revision = 'd617e45b3bef'
down_revision = None
branch_labels = ('kneipy_core',)
depends_on = None


def upgrade():
    op.create_table('balancesheet',
    sa.Column('id', kneipy_core.lib.sqlalchemy_uuid.GUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('name', sa.UnicodeText(), nullable=False),
    sa.Column('transaction_id_seq', sa.BigInteger(), server_default=sa.text("'0'"), nullable=False),
    sa.Column('transaction_group_id_seq', sa.BigInteger(), server_default=sa.text("'0'"), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_balancesheet'))
    )
    op.create_table('person',
    sa.Column('external_refs', postgresql.HSTORE(text_type='str'), nullable=True),
    sa.Column('id', kneipy_core.lib.sqlalchemy_uuid.GUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('name', sa.Unicode(), nullable=False),
    sa.CheckConstraint('\n                (external_refs IS NULL) OR\n                (array_length(akeys(external_refs), 1) > 0)\n            ', name=op.f('ck_person_external_refs_null_or_used')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_person'))
    )
    op.create_table('product',
    sa.Column('id', kneipy_core.lib.sqlalchemy_uuid.GUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('name', sa.Unicode(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product'))
    )
    op.create_table('account',
    sa.Column('external_refs', postgresql.HSTORE(text_type='str'), nullable=True),
    sa.Column('id', kneipy_core.lib.sqlalchemy_uuid.GUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('type', postgresql.ENUM('BalanceSheetOpening', 'Temp', 'Person', 'Result', 'Profits', 'Expenses', 'Balances', name='accounttypes'), nullable=False),
    sa.Column('balancesheet_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=True),
    sa.Column('parent_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=True),
    sa.Column('parent_type', postgresql.ENUM('BalanceSheetOpening', 'Temp', 'Person', 'Result', 'Profits', 'Expenses', 'Balances', name='accounttypes'), nullable=True),
    sa.Column('person_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=True),
    sa.Column('name', sa.Unicode(), nullable=True),
    sa.CheckConstraint("\n            (\n                (type IN (\n                    'Person', 'Result',\n                    'Balances', 'Temp',\n                    'BalanceSheetOpening')\n                ) AND\n                (parent_type IS NULL)\n            ) OR (\n                type = parent_type AND type IS NOT NULL\n            ) OR (\n                type IN ('Profits', 'Expenses') AND parent_type = 'Result'\n            )\n            ", name=op.f('ck_account_parent_type_check')),
    sa.CheckConstraint("\n        (type = 'Temp'     AND person_id IS NULL     AND name IS NULL    ) OR\n        (type = 'Person'   AND person_id IS NOT NULL AND name IS NULL    ) OR\n        (type IN ('Balances', 'Result', 'Profits', 'Expenses') AND\n            person_id IS NULL AND name IS NOT NULL\n        )\n            ", name=op.f('ck_account_type_based_null_check')),
    sa.CheckConstraint('\n                (external_refs IS NULL) OR\n                (array_length(akeys(external_refs), 1) > 0)\n            ', name=op.f('ck_account_external_refs_null_or_used')),
    sa.ForeignKeyConstraint(['balancesheet_id'], ['balancesheet.id'], name=op.f('fk_account_balancesheet_id_balancesheet')),
    sa.ForeignKeyConstraint(['parent_id', 'parent_type'], ['account.id', 'account.type'], name=op.f('fk_account_parent_id_account'), onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], name=op.f('fk_account_person_id_person'), onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_account')),
    sa.UniqueConstraint('type', 'id', name=op.f('uq_account_type'))
    )
    op.create_table('transaction_group',
    sa.Column('balancesheet_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=False),
    sa.Column('id', sa.BigInteger(), server_default=FetchedValue(), nullable=False),
    sa.Column('receiptdate', sa.Date(), server_default=sa.text('now()'), nullable=False),
    sa.Column('receipt', sa.Unicode(), nullable=True),
    sa.Column('bookingtime', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('text', sa.Unicode(), nullable=False),
    sa.Column('external_refs', postgresql.HSTORE(text_type='str'), nullable=True),
    sa.CheckConstraint('\n                (external_refs IS NULL) OR\n                (array_length(akeys(external_refs), 1) > 0)\n            ', name=op.f('ck_transaction_group_external_refs_null_or_used')),
    sa.ForeignKeyConstraint(['balancesheet_id'], ['balancesheet.id'], name=op.f('fk_transaction_group_balancesheet_id_balancesheet'), onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('balancesheet_id', 'id', name=op.f('pk_transaction_group'))
    )
    op.create_index(op.f('ix_transaction_group_receipt'), 'transaction_group', ['receipt'], unique=False)
    op.create_table('transaction',
    sa.Column('balancesheet_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=False),
    sa.Column('id', sa.BigInteger(), server_default=FetchedValue(), nullable=False),
    sa.Column('transaction_group_id', sa.BigInteger(), nullable=False),
    sa.Column('credit_account_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=False),
    sa.Column('debit_account_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=False),
    sa.Column('product_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=False),
    sa.Column('amount', sa.BigInteger(), nullable=False),
    sa.Column('text', sa.Unicode(), nullable=False),
    sa.Column('cancellation_for_transaction_id', sa.BigInteger(), nullable=True),
    sa.CheckConstraint('\n            (amount > 0 AND cancellation_for_transaction_id IS NULL) OR\n            (amount < 0 AND cancellation_for_transaction_id IS NOT NULL)\n        ', name=op.f('ck_transaction_amount')),
    sa.CheckConstraint('credit_account_id != debit_account_id', name=op.f('ck_transaction_not_same_account')),
    sa.ForeignKeyConstraint(['balancesheet_id', 'cancellation_for_transaction_id', 'product_id', 'credit_account_id', 'debit_account_id'], ['transaction.balancesheet_id', 'transaction.id', 'transaction.product_id', 'transaction.credit_account_id', 'transaction.debit_account_id'], name='storno', onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['balancesheet_id', 'transaction_group_id'], ['transaction_group.balancesheet_id', 'transaction_group.id'], name=op.f('fk_transaction_balancesheet_id_transaction_group'), onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['balancesheet_id'], ['balancesheet.id'], name=op.f('fk_transaction_balancesheet_id_balancesheet'), onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['credit_account_id'], ['account.id'], name=op.f('fk_transaction_credit_account_id_account'), onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['debit_account_id'], ['account.id'], name=op.f('fk_transaction_debit_account_id_account'), onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['product_id'], ['product.id'], name=op.f('fk_transaction_product_id_product'), onupdate='RESTRICT', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('balancesheet_id', 'id', name=op.f('pk_transaction')),
    sa.UniqueConstraint('balancesheet_id', 'credit_account_id', 'product_id', 'id', name='uq_transaction_credit'),
    sa.UniqueConstraint('balancesheet_id', 'debit_account_id', 'product_id', 'id', 'credit_account_id', name='uq_transaction_debit')
    )


def downgrade():
    op.drop_table('transaction')
    op.drop_index(op.f('ix_transaction_group_receipt'), table_name='transaction_group')
    op.drop_table('transaction_group')
    op.drop_table('account')
    op.drop_table('product')
    op.drop_table('person')
    op.drop_table('balancesheet')
    op.execute("""
        DROP TYPE accounttypes;
    """)
