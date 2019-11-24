import sqlalchemy as sa
from kneipy_core.lib.sqlalchemy_uuid import GUID
from sqlalchemy.orm import backref, relationship

from .base import Base

SA_AMOUNT_TYPE = sa.Numeric(20, 5)


class Transaction(Base):
    __tablename__ = "transaction"
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            'balancesheet_id',
            'id'
        ),
        # amount has to be positive fpr normal transactions
        # and negative for cancellations
        sa.CheckConstraint('''
            (amount > 0 AND cancellation_for_transaction_id IS NULL) OR
            (amount < 0 AND cancellation_for_transaction_id IS NOT NULL)
        ''', name='amount'),
        # transactions between the same accounts don't make any sense
        sa.CheckConstraint(
            'credit_account_id != debit_account_id',
            name='not_same_account'
        ),

        sa.ForeignKeyConstraint(
            [
                'balancesheet_id',
                'transaction_group_id',
            ], [
                'transaction_group.balancesheet_id',
                'transaction_group.id',
            ],
            onupdate="RESTRICT", ondelete="RESTRICT",
        ),

        # Der folgende ForeignKeyConstraint stellt sicher, dass
        # Storno-Buchungen die gleichen Konten und gleiche Product
        # wie die Original-Buchung haben.
        sa.ForeignKeyConstraint(
            [
                'balancesheet_id',
                'cancellation_for_transaction_id',
                'product_id',
                'credit_account_id',
                'debit_account_id'
            ], [
                'transaction.balancesheet_id',
                'transaction.id',
                'transaction.product_id',
                'transaction.credit_account_id',
                'transaction.debit_account_id'
            ],
            onupdate="RESTRICT", ondelete="RESTRICT",
            name='storno'
        ),
        # Buchungen eines Accounts zu finden kommt häufiger vor
        # id ist ebenfalls im Index um schnell danach sortieren zu können
        # bzw. für range-queries, wie sie für pagination praktisch sind
        sa.UniqueConstraint(
            'balancesheet_id',
            'credit_account_id',
            'product_id',
            'id',
            name='uq_transaction_credit'
        ),
        # Die zusätzlichen Felder hinter id sind für den Foreign Key
        # Constaint oben, der Stornos korrekt erzwingt, leider nötig,
        # auch wenn eigentlich definiv klar ist, dass sie für
        # Eindeutigkeit nicht nötig wären.
        sa.UniqueConstraint(
            'balancesheet_id',
            'debit_account_id',
            'product_id',
            'id',
            'credit_account_id',
            name='uq_transaction_debit'
        ),
        sa.UniqueConstraint(
            'balancesheet_id',
            'cancellation_for_transaction_id',
            name='uq_transaction_cancellation_for_transaction_id'
        ),
        sa.ForeignKeyConstraint([
                'credit_account_id', 'balancesheet_id'
            ], [
                'account.id', 'account.balancesheet_id'
            ],
            onupdate="RESTRICT", ondelete="RESTRICT",
            name='credit_account'
        ),
        sa.ForeignKeyConstraint([
                'debit_account_id', 'balancesheet_id'
            ], [
                'account.id', 'account.balancesheet_id'
            ],
            onupdate="RESTRICT", ondelete="RESTRICT",
            name='debit_account'
        ),
    )
    balancesheet_id = sa.Column(
        sa.ForeignKey(
            'balancesheet.id',
            onupdate="RESTRICT", ondelete="RESTRICT"
        ),
        nullable=False
    )
    id = sa.Column(
        sa.BigInteger,
        server_default=sa.FetchedValue(),
        nullable=False
    )
    balancesheet = relationship('BalanceSheet')

    transaction_group_id = sa.Column(
        sa.BigInteger,
        nullable=False
    )
    transaction_group = relationship(
        'TransactionGroup',
        viewonly=True,
        backref='transactions'
    )

    credit_account_id = sa.Column(
        GUID,
        nullable=False
    )
    credit_account = relationship(
        'Account',
        viewonly=True,
        foreign_keys=[credit_account_id, balancesheet_id]
    )

    debit_account_id = sa.Column(
        GUID,
        nullable=False
    )
    debit_account = relationship(
        'Account',
        viewonly=True,
        foreign_keys=[debit_account_id, balancesheet_id]
    )

    product_id = sa.Column(
        sa.ForeignKey('product.id', onupdate="RESTRICT", ondelete="RESTRICT"),
        nullable=False
    )
    product = relationship('Product')

    amount = sa.Column(SA_AMOUNT_TYPE, nullable=False)

    text = sa.Column(sa.Unicode, nullable=False)

    cancellation_for_transaction_id = sa.Column(
        sa.BigInteger, sa.ForeignKey('transaction.id'),
        nullable=True
    )


Transaction.cancellation_for_transaction = relationship(
    'Transaction',
    backref=backref('cancelled_by', uselist=False),
    remote_side=[
        Transaction.balancesheet_id, Transaction.id, Transaction.product_id,
        Transaction.credit_account_id, Transaction.debit_account_id],
    uselist=False,
    foreign_keys=[
        Transaction.balancesheet_id, Transaction.cancellation_for_transaction_id, Transaction.product_id,
        Transaction.credit_account_id, Transaction.debit_account_id],
)


update_transaction_id_increment_trigger = sa.DDL("""
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
