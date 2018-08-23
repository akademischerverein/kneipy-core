import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.dialects.postgresql.ranges import NUMRANGE
from sqlalchemy.orm import relationship

from kneipy_core.lib.sqlalchemy_uuid import GUID

from .base import Base
from .mixins import ExternalRefMixin


class Report(Base, ExternalRefMixin):
    __tablename__ = 'report'
    batch_id = sa.Column(
        sa.ForeignKey('report_batch.id', onupdate="RESTRICT", ondelete="RESTRICT"),
        nullable=False
    )
    batch = relationship('ReportBatch', backref='reports')

    sequence_id = sa.Column(
        sa.ForeignKey('report_sequence.id', onupdate="RESTRICT", ondelete="RESTRICT"),
        nullable=False
    )
    sequence = relationship('ReportSequence', backref='reports')

    state = sa.Column(
        sa.UnicodeText(),
        nullable=False
    )
    # transactions in failed reports can be "used" in another report
    failed = sa.Column(
        sa.Boolean(), server_default=sa.text('False'),
        nullable=False
    )

    @declared_attr
    def __table_args__(self):
        return tuple(ExternalRefMixin.table_args() + [
            sa.PrimaryKeyConstraint(
                'sequence_id',
                'batch_id'
            ),
            # Needed for fk in report_transactions.
            # The order of batch_id and sequence_id is different
            # than the PK, so queries for all reports for a sequence can use
            # the PK and queries for all reports of a batch can use this.
            sa.UniqueConstraint(
                'batch_id', 'sequence_id', 'failed',
                name='uq_batch_sequence_failed'
            ),

        ])


class ReportBatch(Base, ExternalRefMixin):
    """
    A ReportBatch is a set of independent reports of possibly multiple
    types that are generated at the same time and likely by the same trigger.
    """
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


class ReportSequence(Base, ExternalRefMixin):
    """
    A ReportSequence is a consecutive set of reports where no transaction is
    included in more than one report. Transactions can be included in
    additional reports for informational purposes only (provide context,
    show past values, ...).
    """

    __tablename__ = 'report_sequence'
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
        sa.ForeignKey('person.id', onupdate="RESTRICT", ondelete="RESTRICT"),
        nullable=True
    )
    person = relationship('Person', backref='reports')

    account_id = sa.Column(
        sa.ForeignKey('account.id', onupdate="RESTRICT", ondelete="RESTRICT"),
        nullable=True
    )
    account = relationship('Account', backref='reports')

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


class ReportTransactions(Base):
    __tablename__ = 'report_transactions'
    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )
    batch_id = sa.Column(sa.ForeignKey(
        'report_batch.id', onupdate="RESTRICT", ondelete="RESTRICT"
    ), nullable=False)
    batch = relationship('ReportBatch')

    sequence_id = sa.Column(sa.ForeignKey(
        'report_sequence.id', onupdate="RESTRICT", ondelete="RESTRICT"
    ), nullable=False)
    sequence = relationship('ReportSequence')

    balancesheet_id = sa.Column(sa.ForeignKey(
        'balancesheet.id',
        onupdate="RESTRICT",
        ondelete="RESTRICT"
    ), nullable=False)
    balancesheet = relationship('BalanceSheet')

    transaction_id_range = sa.Column(NUMRANGE, nullable=False)

    only_informational = sa.Column(sa.Boolean(), server_default=sa.text('False'), nullable=False)
    failed = sa.Column(sa.Boolean(), nullable=False)

    @declared_attr
    def __table_args__(self):
        return tuple([
            # this keeps the failed column in sync with the report table
            # it's needed for the exclusion constraints below
            sa.ForeignKeyConstraint(
                ['batch_id', 'sequence_id', 'failed'],
                ['report.batch_id', 'report.sequence_id', 'report.failed'],
                onupdate="CASCADE", ondelete="RESTRICT",
                name="fk_batch_sequence_failed"
            ),
            ExcludeConstraint(
                ('sequence_id', '='), ('balancesheet_id', '='), ('transaction_id_range', '&&'),
                where=(~self.only_informational & ~self.failed),
                name='ex_report_transactions_once_non_informational_per_sequence'
            ),
            ExcludeConstraint(
                ('sequence_id', '='), ('batch_id', '='), ('balancesheet_id', '='), ('transaction_id_range', '&&'),
                name='ex_report_transactions_once_per_report'
            )
        ])
