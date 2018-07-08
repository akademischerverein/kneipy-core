"""company to group balancesheets

Revision ID: faf6d7094ae3
Revises: 7ef655f56d9d
Create Date: 2017-10-21 00:01:00.510553

"""
from alembic import op
import sqlalchemy as sa
import kneipy_core
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'faf6d7094ae3'
down_revision = '7ef655f56d9d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('company',
    sa.Column('id', sa.BigInteger, autoincrement=True, nullable=False),
    sa.Column('name', sa.UnicodeText(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_company')),
    sa.UniqueConstraint('name', name=op.f('uq_company_name'))
    )
    op.add_column('balancesheet', sa.Column('company_id', sa.BigInteger, nullable=False))
    op.add_column('balancesheet', sa.Column('daterange', postgresql.DATERANGE(), nullable=True))
    op.create_foreign_key(op.f('fk_balancesheet_company_id_company'), 'balancesheet', 'company', ['company_id'], ['id'], onupdate='RESTRICT', ondelete='RESTRICT')
    op.execute('''
        ALTER TABLE balancesheet
            ADD CONSTRAINT ex_balancesheet_company_id_daterange
            EXCLUDE USING gist (company_id WITH =, daterange WITH &&);
    ''')


def downgrade():
    op.execute('''
        ALTER TABLE balancesheet
            DROP CONSTRAINT ex_balancesheet_company_id_daterange;
    ''')
    op.drop_constraint(op.f('fk_balancesheet_company_id_company'), 'balancesheet', type_='foreignkey')
    op.drop_column('balancesheet', 'daterange')
    op.drop_column('balancesheet', 'company_id')
    op.drop_table('company')
