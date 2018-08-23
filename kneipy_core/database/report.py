import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.dialects.postgresql.ranges import NUMRANGE
from sqlalchemy.dialects.postgresql.array import ARRAY
from sqlalchemy.orm import relationship

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

    batch_id = sa.Column(
        sa.ForeignKey('report_batch.id', onupdate="RESTRICT", ondelete="RESTRICT"),
        nullable=False
    )
    batch = relationship('ReportBatch', backref='reports')

    person_id = sa.Column(
        sa.ForeignKey('person.id', onupdate="RESTRICT", ondelete="RESTRICT"),
        nullable=True
    )
    person = relationship('Person', backref='reports')

    account_id = sa.Column(
        sa.ForeignKey('account.id', onupdate="RESTRICT", ondelete="RESTRICT"),
        nullable=True
    )
    account = relationship('Account', backref='reports')

    state = sa.Column(
        sa.UnicodeText(),
        nullable=False
    )

    @declared_attr
    def __table_args__(self):
        return tuple(ExternalRefMixin.table_args() + [
            sa.CheckConstraint(
                '''
                (person_id IS NULL) OR
                (account_id IS NULL)
                ''',
                name='account_or_person_null'
            )
        ])


class ReportBatch(Base, ExternalRefMixin):
    __tablename__ = 'report_batch'
    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )
    generated_at = sa.Column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now()
    )
    state = sa.Column(
        sa.UnicodeText(),
        nullable=False
    )

    @declared_attr
    def __table_args__(self):
        return tuple(ExternalRefMixin.table_args())


class ReportTransactions(Base):
    __tablename__ = 'report_transactions'
    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )
    report_id = sa.Column(sa.ForeignKey(
        'report.id',
        onupdate="RESTRICT",
        ondelete="RESTRICT"
    ), nullable=False)
    balancesheet_id = sa.Column(sa.ForeignKey(
        'balancesheet.id',
        onupdate="RESTRICT",
        ondelete="RESTRICT"
    ), nullable=False)
    transaction_id_range = sa.Column(NUMRANGE, nullable=False)
    only_informational = sa.Column(sa.Boolean(), server_default=sa.text('False'), nullable=False)

    @declared_attr
    def __table_args__(self):
        return tuple([
            ExcludeConstraint(
                ('balancesheet_id', '='), ('report_id', '='),
                ('transaction_id_range', '&&'),
                name='ex_report_transaction_report_id_balancesheet_id_transaction_id_range',
                where=(~self.only_informational)
            )
        ])
