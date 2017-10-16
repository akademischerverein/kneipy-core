"""triggers for gapless sequence

Revision ID: ae1f9f33b46c
Revises: b5be6a74277c
Create Date: 2017-10-16 02:46:41.626574

"""
from alembic import op
import sqlalchemy as sa
import kneipy_core


# revision identifiers, used by Alembic.
revision = 'ae1f9f33b46c'
down_revision = 'd617e45b3bef'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE OR REPLACE FUNCTION transaction_id_increment()
        RETURNS "trigger" AS
        '
        BEGIN
            UPDATE balancesheet
                SET transaction_id_seq = (transaction_id_seq + 1)
                WHERE balancesheet.id = NEW.balancesheet_id;
            SELECT INTO NEW.id transaction_id_seq
                FROM balancesheet WHERE id = NEW.balancesheet_id;
        RETURN new;
        END;
        '
        LANGUAGE 'plpgsql' VOLATILE;

        CREATE TRIGGER transaction_id_increment
            BEFORE INSERT
            ON transaction
            FOR EACH ROW
            EXECUTE PROCEDURE transaction_id_increment();
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION transaction_group_id_increment()
        RETURNS "trigger" AS
        '
        BEGIN
            UPDATE balancesheet
                SET transaction_group_id_seq = (transaction_group_id_seq + 1)
                WHERE balancesheet.id = NEW.balancesheet_id;
            SELECT INTO NEW.id transaction_group_id_seq
                FROM balancesheet WHERE id = NEW.balancesheet_id;
        RETURN new;
        END;
        '
        LANGUAGE 'plpgsql' VOLATILE;

        CREATE TRIGGER transaction_group_id_increment
            BEFORE INSERT
            ON transaction_group
            FOR EACH ROW
            EXECUTE PROCEDURE transaction_group_id_increment();
    """)


def downgrade():
    op.execute("""
        DROP TRIGGER transaction_group_id_increment ON transaction_group;
        DROP TRIGGER transaction_id_increment ON transaction;
        DROP FUNCTION transaction_group_id_increment();
        DROP FUNCTION transaction_id_increment();
    """)
