from .base import Base
import sqlalchemy as sa
from sqlalchemy.orm import relationship


class Transaction(Base):
    __tablename__ = "transaction"
    __table_args__ = (
        # amount muss größer Null sein, bei Stornos -amount der Original Buchung
        # => kleiner Null
        sa.CheckConstraint('''
            (amount > 0 AND cancellation_for_transaction_id IS NULL) OR
            (amount < 0 AND cancellation_for_transaction_id IS NOT NULL)
        ''', name='transaction_amount_check'),
        sa.CheckConstraint(
            'credit_account_id != debit_account_id',
            name='transaction_not_same_account_check'
        ),

        # Der folgende ForeignKeyConstraint stellt sicher, dass
        # Storno-Buchungen die gleichen Konten und gleiche Product
        # wie die Original-Buchung haben.
        sa.ForeignKeyConstraint(
            [
                'credit_account_id',
                'cancellation_for_transaction_id',
                'debit_account_id',
                'product_id',
            ], [
                'transaction.credit_account_id',
                'transaction.id',
                'transaction.debit_account_id',
                'transaction.product_id',
            ],
            onupdate="RESTRICT", ondelete="RESTRICT",
            name='transaction_storno_fk'
        ),
        # Buchungen eines Accounts zu finden kommt häufiger vor
        # id ist ebenfalls im Index um schnell danach sortieren zu können
        # bzw. für range-queries, wie sie für pagination praktisch sind
        sa.UniqueConstraint(
            'credit_account_id',
            'product_id',
            'id',
            name='transaction_credit_unique'
        ),
        # Die zusätzlichen Felder hinter id sind für den Foreign Key
        # Constaint oben, der Stornos korrekt erzwingt, leider nötig,
        # auch wenn eigentlich definiv klar ist, dass sie für
        # Eindeutigkeit nicht nötig wären.
        sa.UniqueConstraint(
            'debit_account_id',
            'product_id',
            'id',
            'credit_account_id',
            name='transaction_dedit_unique'
        ),
    )
    id = sa.Column(
        sa.BigInteger,
        primary_key=True,
        autoincrement=True
    )
    transaction_group_id = sa.Column(
        sa.ForeignKey('transaction_group.id'),
        nullable=False,
        index=True
    )

    credit_account_id = sa.Column(
        sa.ForeignKey('account.id', onupdate="RESTRICT", ondelete="RESTRICT"),
        nullable=False
    )
    credit_account = relationship('Account', foreign_keys=[credit_account_id])
    debit_account_id = sa.Column(
        sa.ForeignKey('account.id', onupdate="RESTRICT", ondelete="RESTRICT"),
        nullable=False
    )
    debit_account = relationship('Account', foreign_keys=[debit_account_id])

    product_id = sa.Column(
        sa.ForeignKey('product.id', onupdate="RESTRICT", ondelete="RESTRICT"),
        nullable=False
    )
    product = relationship('Product')
    amount = sa.Column(sa.BigInteger, nullable=False)

    text = sa.Column(sa.Unicode, nullable=False)

    cancellation_for_transaction_id = sa.Column(sa.BigInteger, nullable=True)
    cancellation_for_transaction = relationship(
        'Transaction',
        back_populates='cancelled_by',
        primaryjoin=(cancellation_for_transaction_id == id),
        remote_side=[id],
        uselist=False
    )
    cancelled_by = relationship(
        'Transaction',
        back_populates='cancellation_for_transaction',
        primaryjoin=(cancellation_for_transaction_id == id),
        remote_side=[cancellation_for_transaction_id],
        uselist=False
    )
