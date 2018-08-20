import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql.ranges import NUMRANGE
from sqlalchemy.dialects.postgresql.array import ARRAY

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
    datetime = sa.Column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now()
    )
    parent = sa.Column(sa.ForeignKey(
        'report.id', onupdate="RESTRICT", ondelete="RESTRICT"
    ), nullable=True)
    context_id = sa.Column(sa.ForeignKey(
        'report_context.id', onupdate="RESTRICT", ondelete="RESTRICT"
    ))

    @declared_attr
    def __table_args__(self):
        return tuple(ExternalRefMixin.table_args())


class ReportContext(Base, ExternalRefMixin):
    __tablename__ = 'report_context'
    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )
    person_id = sa.Column(
        sa.ForeignKey('person.id', onupdate="RESTRICT", ondelete="RESTRICT"),
        nullable=True
    )

    @declared_attr
    def __table_args__(self):
        return tuple(ExternalRefMixin.table_args())


class ReportContextMapping(Base):
    __tablename__ = 'report_context_mapping'
    __table_args__ = (
        sa.PrimaryKeyConstraint(
            'report_context_id',
            'balancesheet_id'
        ),
    )

    report_context_id = sa.Column(sa.ForeignKey(
        'report_context.id',
        onupdate="RESTRICT",
        ondelete="RESTRICT"
    ))
    balancesheet_id = sa.Column(sa.ForeignKey(
        'balancesheet.id',
        onupdate="RESTRICT",
        ondelete="RESTRICT"
    ))
    transaction_id_range = sa.Column(NUMRANGE, nullable=False)
    # TODO: foreign key on transaction id range
