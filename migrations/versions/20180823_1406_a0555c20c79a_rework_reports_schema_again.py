"""rework reports schema again

Revision ID: a0555c20c79a
Revises: e475c073dc7a
Create Date: 2018-08-23 14:06:15.009280

"""
from alembic import op
import sqlalchemy as sa
import kneipy_core
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a0555c20c79a'
down_revision = 'e475c073dc7a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'report_sequence',
        sa.Column('external_refs', postgresql.HSTORE(text_type=sa.Text()), nullable=True),
        sa.Column('id', kneipy_core.lib.sqlalchemy_uuid.GUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('type', sa.UnicodeText(), nullable=False),
        sa.Column('person_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=True),
        sa.Column('account_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=True),
        sa.CheckConstraint('\n                (external_refs IS NULL) OR\n                (array_length(akeys(external_refs), 1) > 0)\n            ', name=op.f('ck_report_sequence_external_refs_null_or_used')),
        sa.CheckConstraint('\n                (person_id IS NULL) OR\n                (account_id IS NULL)\n                ', name=op.f('ck_report_sequence_account_or_person_null')),
        sa.ForeignKeyConstraint(['account_id'], ['account.id'], name=op.f('fk_report_sequence_account_id_account'), onupdate='RESTRICT', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['person_id'], ['person.id'], name=op.f('fk_report_sequence_person_id_person'), onupdate='RESTRICT', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_report_sequence'))
    )

    op.drop_constraint('fk_report_person_id_person', 'report', type_='foreignkey')
    op.drop_constraint('fk_report_account_id_account', 'report', type_='foreignkey')
    op.drop_constraint('fk_report_transactions_report_id_report', 'report_transactions', type_='foreignkey')

    op.drop_column('report_transactions', 'report_id')
    op.add_column('report', sa.Column('failed', sa.Boolean(), server_default=sa.text('False'), nullable=False))
    op.add_column('report', sa.Column('sequence_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=False))
    op.drop_column('report', 'person_id')
    op.drop_column('report', 'account_id')
    op.drop_column('report', 'id')
    op.drop_column('report', 'type')
    op.create_primary_key('pk_report', 'report', ['sequence_id', 'batch_id'])
    op.create_unique_constraint('uq_batch_sequence_failed', 'report', ['batch_id', 'sequence_id', 'failed'])

    op.create_foreign_key(op.f('fk_report_sequence_id_report_sequence'), 'report', 'report_sequence', ['sequence_id'], ['id'], onupdate='RESTRICT', ondelete='RESTRICT')
    op.add_column('report_transactions', sa.Column('batch_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=False))
    op.add_column('report_transactions', sa.Column('failed', sa.Boolean(), nullable=False))
    op.add_column('report_transactions', sa.Column('sequence_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=False))
    op.create_foreign_key(op.f('fk_report_transactions_sequence_id_report_sequence'), 'report_transactions', 'report_sequence', ['sequence_id'], ['id'], onupdate='RESTRICT', ondelete='RESTRICT')
    op.create_foreign_key('fk_batch_sequence_failed', 'report_transactions', 'report', ['batch_id', 'sequence_id', 'failed'], ['batch_id', 'sequence_id', 'failed'], onupdate='CASCADE', ondelete='RESTRICT')
    op.create_foreign_key(op.f('fk_report_transactions_batch_id_report_batch'), 'report_transactions', 'report_batch', ['batch_id'], ['id'], onupdate='RESTRICT', ondelete='RESTRICT')


def downgrade():
    op.drop_constraint(op.f('fk_report_transactions_batch_id_report_batch'), 'report_transactions', type_='foreignkey')
    op.drop_constraint('fk_batch_sequence_failed', 'report_transactions', type_='foreignkey')
    op.drop_constraint(op.f('fk_report_transactions_sequence_id_report_sequence'), 'report_transactions', type_='foreignkey')
    op.drop_constraint(op.f('fk_report_sequence_id_report_sequence'), 'report', type_='foreignkey')
    op.drop_constraint('uq_batch_sequence_failed', 'report', type_='unique')

    op.add_column('report_transactions', sa.Column('report_id', postgresql.UUID(), autoincrement=False, nullable=False))
    op.add_column('report', sa.Column('type', sa.TEXT(), autoincrement=False, nullable=False))
    op.add_column('report', sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), autoincrement=False, nullable=False))
    op.add_column('report', sa.Column('account_id', postgresql.UUID(), autoincrement=False, nullable=True))
    op.add_column('report', sa.Column('person_id', postgresql.UUID(), autoincrement=False, nullable=True))

    op.drop_column('report_transactions', 'sequence_id')
    op.drop_column('report_transactions', 'failed')
    op.drop_column('report_transactions', 'batch_id')
    op.drop_column('report', 'sequence_id')
    op.drop_column('report', 'failed')
    op.drop_table('report_sequence')

    op.create_primary_key('pk_report', 'report', ['id'])

    op.create_foreign_key('fk_report_transactions_report_id_report', 'report_transactions', 'report', ['report_id'], ['id'], onupdate='RESTRICT', ondelete='RESTRICT')
    op.create_foreign_key('fk_report_account_id_account', 'report', 'account', ['account_id'], ['id'], onupdate='RESTRICT', ondelete='RESTRICT')
    op.create_foreign_key('fk_report_person_id_person', 'report', 'person', ['person_id'], ['id'], onupdate='RESTRICT', ondelete='RESTRICT')
