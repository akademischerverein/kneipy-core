"""GUID in company

Revision ID: 85259ae189f6
Revises: 9d5bcbef0c91
Create Date: 2018-08-23 11:54:10.758895

"""
from alembic import op
import sqlalchemy as sa
import kneipy_core


# revision identifiers, used by Alembic.
revision = '85259ae189f6'
down_revision = '9d5bcbef0c91'
branch_labels = None
depends_on = None


def upgrade():
    # Drop primary key constraint. Note the CASCASE clause - this deletes the foreign key constraint.
    op.execute('ALTER TABLE company DROP CONSTRAINT pk_company CASCADE')
    op.alter_column('company', 'id', new_column_name='old_id')
    op.add_column(
        'company',
        sa.Column('id', kneipy_core.lib.sqlalchemy_uuid.GUID(),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
    )
    op.create_primary_key('pk_company', 'company', ['id'])

    op.drop_constraint(
        op.f('ex_balancesheet_company_id_daterange'),
        'balancesheet', type_='foreignkey')
    op.alter_column('balancesheet', 'company_id', new_column_name='old_company_id')
    op.add_column(
        'balancesheet',
        sa.Column('company_id', kneipy_core.lib.sqlalchemy_uuid.GUID(), nullable=True)
    )
    op.execute('''
        ALTER TABLE balancesheet
            ADD CONSTRAINT ex_balancesheet_company_id_daterange
            EXCLUDE USING gist (company_id WITH =, daterange WITH &&);
    ''')
    op.create_foreign_key(op.f('fk_balancesheet_company_id_company'), 'balancesheet', 'company', ['company_id'], ['id'], onupdate='RESTRICT', ondelete='RESTRICT')
    op.execute('''
        UPDATE
            balancesheet
        SET
            company_id=c.id
        FROM (
            SELECT
                id, old_id
            FROM
                company
        ) AS c
        WHERE
            balancesheet.old_company_id = c.old_id
    ''')
    op.drop_column('company', 'old_id')
    op.drop_column('balancesheet', 'old_company_id')
    op.alter_column('balancesheet', 'company_id', nullable=False)
    op.execute('''
        DROP SEQUENCE IF EXISTS company_id_seq
    ''')


def downgrade():
    op.execute('ALTER TABLE company DROP CONSTRAINT pk_company CASCADE')
    op.alter_column('company', 'id', new_column_name='old_id')
    op.execute('''
        CREATE SEQUENCE company_id_seq
    ''')
    op.add_column(
        'company',
        sa.Column('id', sa.BigInteger(), server_default=sa.func.nextval('company_id_seq')),
    )
    op.create_primary_key('pk_company', 'company', ['id'])

    op.drop_constraint(
        op.f('ex_balancesheet_company_id_daterange'),
        'balancesheet', type_='foreignkey')
    op.alter_column('balancesheet', 'company_id', new_column_name='old_company_id')
    op.add_column(
        'balancesheet',
        sa.Column('company_id', sa.BigInteger(), nullable=True)
    )
    op.execute('''
        ALTER TABLE balancesheet
            ADD CONSTRAINT ex_balancesheet_company_id_daterange
            EXCLUDE USING gist (company_id WITH =, daterange WITH &&);
    ''')
    op.create_foreign_key(op.f('fk_balancesheet_company_id_company'), 'balancesheet', 'company', ['company_id'], ['id'], onupdate='RESTRICT', ondelete='RESTRICT')
    op.execute('''
        UPDATE
            balancesheet
        SET
            company_id=c.id
        FROM (
            SELECT
                id, old_id
            FROM
                company
        ) AS c
        WHERE
            balancesheet.old_company_id = c.old_id
    ''')
    op.drop_column('company', 'old_id')
    op.drop_column('balancesheet', 'old_company_id')
    op.alter_column('balancesheet', 'company_id', nullable=False)
