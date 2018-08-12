import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql.ranges import NUMRANGE

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
    transaction_ids = sa.Column(sa.Array(NUMRANGE), nullable=False)
    person_id = sa.Column(sa.ForeignKey('person.id'), nullable=True)

    @declared_attr
    def __table_args__(self):
        return tuple([
            # TODO: ForeignKeyConstraint für alle balancesheet ids vs transaction ids
            sa.CheckConstraint("""
                array_length(balancesheet_ids, 1)=array_length(transaction_ids, 1)
            """, name='balancesheets_transactions_array_length_check'),
        ])
