import sqlalchemy as sa

from kneipy_core.lib.sqlalchemy_uuid import GUID

from .base import Base


class Report(Base):
    __tablename__ = 'report'
    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )
    type = sa.Column(
        sa.UnicodeText(),
        nullable=False
    )
    person_id = sa.Column(
        sa.ForeignKey('person.id')
    )
    balancesheet_id = sa.Column(
        sa.ForeignKey('AccountBalanceSheet.id')
    )
    up_to_transaction_id = sa.Column(
        sa.ForeignKey('Transaction.id'),
        nullable=False
    )
