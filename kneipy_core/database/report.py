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
    person_id = sa.Column(
        sa.ForeignKey('person.id')
    )
    balancesheet_id = sa.Column(GUID, nullable=False)
    up_to_transaction_id = sa.Column(sa.BigInteger, nullable=False)

    @declared_attr
    def __table_args__(self):
        return tuple(ExternalRefMixin.table_args() + [
            sa.ForeignKeyConstraint(
                [
                    'balancesheet_id',
                    'up_to_transaction_id',
                ], [
                    'transaction.balancesheet_id',
                    'transaction.id',
                ],
                onupdate="RESTRICT", ondelete="RESTRICT"
            )
        ])
