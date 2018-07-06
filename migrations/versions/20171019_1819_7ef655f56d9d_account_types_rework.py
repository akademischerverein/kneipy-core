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


def constraint_exists(name):
    rows = op.get_bind().execute(sa.sql.text("""
    SELECT * FROM information_schema.check_constraints WHERE
    constraint_schema = 'public' AND constraint_name = :name
    """), {"name": name}).fetchall()
    return len(rows) > 0


def change_enum(table, column_names, name, new_values):
    # This constraint is supposed to be created in
    # 20171016_0246_d617e45b3bef_initial.py. However it - for some
    # reason - is not present in the database afterwards.
    # If that bug (?) is ever fixed, this migration will break,
    # because this constraint uses the account_type enum.
    # Let's just drop it, it get's created correctly again in
    # 20180706_1753_04c4aa99f54b_create_two_check_constraints_the_.py
    if constraint_exists('ck_account_type_based_null_check'):
        op.drop_constraint(
            'ck_account_type_based_null_check',
            'account'
        )

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
