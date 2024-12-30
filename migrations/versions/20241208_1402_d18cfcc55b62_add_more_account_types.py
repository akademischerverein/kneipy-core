"""add_more_account_types

Revision ID: d18cfcc55b62
Revises: 437625b16fbc
Create Date: 2024-12-08 14:02:52.934250

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd18cfcc55b62'
down_revision = '437625b16fbc'
branch_labels = None
depends_on = None


def constraint_exists(name):
    rows = op.get_bind().execute(sa.sql.text("""
    SELECT * FROM information_schema.check_constraints WHERE
    constraint_schema = 'public' AND constraint_name = :name
    """), {"name": name}).fetchall()
    return len(rows) > 0


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
        'Person', 'ConcessionsLicenses',
        'Goodwill', 'AdvancePayments',
        'PlotsRightsBuildings', 'TechnicalEquipmentAndMachinery',
        'OtherAttachmentsFixtures', 'AdvancePaymentsConstruction',
        'SharesAffiliatedCompanies', 'LoansAffiliatedCompanies',
        'Investments', 'LoansInvestments',
        'Securites', 'OtherLoads',
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
    if not constraint_exists('ck_account_type_based_null_check'):
        op.create_check_constraint(
            op.f('ck_account_type_based_null_check'),
            'account',
            """
            (type = 'Person' AND person_id IS NOT NULL AND name IS NULL) OR
            (type = 'Temp'   AND person_id IS NULL     AND name IS NULL) OR
            (type NOT IN ('Person', 'Temp') AND
                person_id IS NULL AND name IS NOT NULL
            )
            """
        )
