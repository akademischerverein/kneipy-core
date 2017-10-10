import sqlalchemy as sa

from .base import Base


class TransactionGroup(Base):
    __tablename__ = "transaction_group"
    id = sa.Column(
        sa.BigInteger,
        primary_key=True,
        autoincrement=True
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
