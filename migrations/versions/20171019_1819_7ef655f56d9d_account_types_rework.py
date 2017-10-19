"""account.types rework

Revision ID: 7ef655f56d9d
Revises: 433ba863f610
Create Date: 2017-10-19 18:19:07.046875

"""
from alembic import op
import sqlalchemy as sa
import kneipy_core
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7ef655f56d9d'
down_revision = '433ba863f610'
branch_labels = None
depends_on = None


def change_enum(table, column_names, name, new_values):
    op.execute('''
        ALTER TYPE {name} RENAME TO {name}_old;
        CREATE TYPE {name} AS ENUM (
            {values}
        );
    '''.format(
        name=name,
        values=', '.join(
            "'{}'".format(v) for v in new_values
        ))
    )
    for column_name in column_names:
        op.alter_column(
            table, column_name,
            new_column_name=column_name + '_old'
        )
        op.add_column(
            table,
            sa.Column(
                column_name,
                postgresql.ENUM(
                    *new_values,
                    name=name
                ),
            )
        )
        op.execute('''
            UPDATE {table} SET
            {column_name} = {column_name}_old::text::{name};
        '''.format(
            table=table,
            column_name=column_name,
            name=name
        ))
        op.drop_column(table, column_name + '_old')

    op.execute('DROP TYPE {}_old;'.format(name))


def upgrade():
    new_values = [
        'BalanceSheetOpening', 'Temp',
        'Financial', 'Capital',
        'PreviousResults', 'Profits',
        'Expenses', 'FromSales',
        'Transit', 'ConnectedEntities',
        'Others', 'Depreciation',
        'Person'
    ]
    op.drop_constraint(
        'fk_account_parent_id_account',
        'account', type_='foreignkey'
    )
    op.drop_constraint('uq_account_type', 'account', type_='unique')
    change_enum(
        table='account',
        column_names=['type', 'parent_type'],
        name='accounttypes',
        new_values=new_values
    )
    op.alter_column(
        'account', 'type',
        existing_type=postgresql.ENUM(
            *new_values,
            name='accounttypes'
        ),
        nullable=False
    )

    op.create_unique_constraint(op.f('uq_account_type'), 'account', ['type', 'id'])
    op.create_foreign_key(op.f('fk_account_parent_id_account'), 'account', 'account', ['parent_id', 'parent_type'], ['id', 'type'], onupdate='RESTRICT', ondelete='RESTRICT')


def downgrade():
    new_values = [
        'BalanceSheetOpening', 'Temp', 'Person',
        'Result', 'Profits', 'Expenses', 'Balances'
    ]

    op.drop_constraint(
        'fk_account_parent_id_account',
        'account', type_='foreignkey'
    )
    op.drop_constraint('uq_account_type', 'account', type_='unique')
    change_enum(
        table='account',
        column_names=['type', 'parent_type'],
        name='accounttypes',
        new_values=new_values
    )
    op.alter_column(
        'account', 'type',
        existing_type=postgresql.ENUM(
            *new_values,
            name='accounttypes'
        ),
        nullable=False
    )

    op.create_unique_constraint(op.f('uq_account_type'), 'account', ['type', 'id'])
    op.create_foreign_key(op.f('fk_account_parent_id_account'), 'account', 'account', ['parent_id', 'parent_type'], ['id', 'type'], onupdate='RESTRICT', ondelete='RESTRICT')
