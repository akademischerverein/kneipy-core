from contextlib import contextmanager

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import DATERANGE, \
    ExcludeConstraint

from kneipy_core.lib.sqlalchemy_uuid import GUID

from .base import Base
from .util import add_totals_and_balance


class BalanceSheet(Base):
    __tablename__ = 'balancesheet'
    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )

    name = sa.Column(
        sa.UnicodeText,
        nullable=False
    )

    company_id = sa.Column(
        sa.ForeignKey(
            'company.id',
            onupdate="RESTRICT", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    company = relationship('Company', backref='balancesheets')

    daterange = sa.Column(DATERANGE())

    transaction_id_seq = sa.Column(
        sa.BigInteger,
        nullable=False,
        server_default=sa.literal('0')
    )
    transaction_group_id_seq = sa.Column(
        sa.BigInteger,
        nullable=False,
        server_default=sa.literal('0')
    )

    top_level_accounts = relationship(
        'Account', primaryjoin=(
            'and_(' +
            '   Account.parent_id.is_(None),' +
            '   Account.balancesheet_id == BalanceSheet.id' +
            ')'
        )
    )

    accounts = relationship(
        'Account', back_populates='balancesheet'
    )

    __table_args__ = (
        ExcludeConstraint(
            ('company_id', '='), ('daterange', '&&'),
            name='ex_balancesheet_company_id_daterange'
        ),
    )

    @property
    def cumulative_totals_and_balance(self):
        res = {}
        # 10 Ebenen des Konten-Baumes laden mit einem Query pro Ebene
        # Kostet leider einen zusätzlich, da die aktuelle Instanz
        # erneut geladen wird
        instance_state = sa.inspect(self)
        if 'top_level_accounts' in instance_state.unloaded:
            # eager load 10 Ebenen, inkl. der Summen und Salden
            query_options = sa.orm.selectinload('top_level_accounts')
            query_options = query_options.undefer('totals_and_balance')
            for _ in range(10):
                query_options = query_options \
                    .selectinload('children')\
                    .undefer('totals_and_balance')

            instance_state.session.query(self.__class__) \
                .options(query_options) \
                .filter_by(id=self.id).all()

        for account in self.top_level_accounts:
            ctab = account.cumulative_totals_and_balance
            for product_id, data in ctab.items():
                if product_id not in res:
                    res[product_id] = data
                else:
                    res[product_id] = add_totals_and_balance(
                        res[product_id], data
                    )
        return res

    @contextmanager
    def transact_orm(self, text, receiptdate, receipt):
        from ..api import transaction_group_orm  # avoid a circular import

        with transaction_group_orm(
                balancesheet=self,
                text=text, receiptdate=receiptdate, receipt=receipt
                ) as transaction_group:
            yield transaction_group

    @contextmanager
    def transact_core(self, text, receiptdate, receipt):
        from ..api import transaction_group_core  # avoid a circular import

        with transaction_group_core(
                session=sa.orm.object_session(self),
                balancesheet_id=self.id,
                text=text, receiptdate=receiptdate, receipt=receipt
                ) as transaction_group:
            yield transaction_group
