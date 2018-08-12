import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr

from kneipy_core.lib.sqlalchemy_uuid import GUID

from .base import Base
from .mixins import ExternalRefMixin


class Report(Base, ExternalRefMixin):
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
    context_id = sa.Column(sa.ForeignKey('report_context.id'))


class ReportContext(Base):
    __tablename__ = 'report_context'
    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )
    balancesheet_ids = sa.Column(sa.Array(GUID), nullable=False)
    from_transaction_ids = sa.Column(sa.Array(sa.BigInteger), nullable=False)
    up_to_transaction_ids = sa.Column(sa.Array(sa.BigInteger), nullable=False)
    person_id = sa.Column(sa.ForeignKey('person.id'), nullable=True)

    @declared_attr
    def __table_args__(self):
        return tuple([
            # TODO: ForeignKeyConstraint für alle balancesheet ids vs transaction ids
            sa.CheckConstraint("""
                array_length(balancesheet_ids, 1)=array_length(from_transaction_ids, 1) AND
                array_length(from_transaction_ids, 1)=array_length(up_to_transaction_ids)
            """, name='balancesheets_transactions_array_length_check'),
        ])
