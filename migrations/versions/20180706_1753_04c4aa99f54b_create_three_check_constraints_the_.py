"""create three check constraints the initial migration failed to create

Revision ID: 04c4aa99f54b
Revises: b8acb5119512
Create Date: 2018-07-06 17:53:45.904755

"""
from alembic import op
import sqlalchemy as sa
import kneipy_core


# revision identifiers, used by Alembic.
revision = '04c4aa99f54b'
down_revision = 'b8acb5119512'
branch_labels = None
depends_on = None


def constraint_exists(name):
    rows = op.get_bind().execute(sa.sql.text("""
    SELECT * FROM information_schema.check_constraints WHERE
    constraint_schema = 'public' AND constraint_name = :name
    """), {"name": name}).fetchall()
    return len(rows) > 0


def upgrade():
    # An old version of these constraints is supposed to be created in
    # 20171016_0246_d617e45b3bef_initial.py. However they - for some
    # reason - are not present in the database afterwards.
    # These checks are to make sure if that bug (?) is fixed in the future,
    # the migrations don't break horribly.
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
    if not constraint_exists('ck_account_external_refs_null_or_used'):
        op.create_check_constraint(
            op.f('ck_account_external_refs_null_or_used'),
            'account',
            """
            (external_refs IS NULL) OR
            (array_length(akeys(external_refs), 1) > 0)
            """
        )
    if not constraint_exists('ck_account_external_refs_null_or_used'):
        op.create_check_constraint(
            op.f('ck_account_external_refs_null_or_used'),
            'account',
            """
            (external_refs IS NULL) OR
            (array_length(akeys(external_refs), 1) > 0)
            """
        )
    if not constraint_exists('ck_account_parent_type_check'):
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


def downgrade():
    op.drop_constraint(
        'ck_account_type_based_null_check',
        'account'
    )
    op.drop_constraint(
        'ck_account_external_refs_null_or_used',
        'account'
    )
    op.drop_constraint(
        'ck_account_parent_type_check',
        'account'
    )
