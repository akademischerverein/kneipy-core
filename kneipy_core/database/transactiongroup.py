import sqlalchemy as sa
from sqlalchemy.orm import relationship

from .base import Base


class TransactionGroup(Base):
    __tablename__ = "transaction_group"
    balancesheet_id = sa.Column(
        sa.ForeignKey(
            'balancesheet.id',
            onupdate="RESTRICT", ondelete="RESTRICT"
        ),
        nullable=False
    )
    balancesheet = relationship('BalanceSheet')
    id = sa.Column(
        sa.BigInteger,
        server_default=sa.FetchedValue(),
        nullable=False
    )
    receiptdate = sa.Column(
        sa.Date,
        nullable=False,
        server_default=sa.func.now()
    )
    receipt = sa.Column(
        sa.Unicode,
        nullable=True,
        index=True
    )
    bookingtime = sa.Column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now()
    )
    text = sa.Column(
        sa.Unicode,
        nullable=False
    )

    __table_args__ = (
        sa.PrimaryKeyConstraint(
            'balancesheet_id', 'id'
        ),
    )


update_transaction_group_id_increment_trigger = sa.DDL("""
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
