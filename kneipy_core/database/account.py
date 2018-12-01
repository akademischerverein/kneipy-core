import collections
import enum

import sqlalchemy as sa
from kneipy_core.lib.sqlalchemy_uuid import GUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

from .balancesheet import BalanceSheet
from .base import Base
from .mixins import ExternalRefMixin
from .product import Product
from .transaction import SA_AMOUNT_TYPE, Transaction
from .transactiongroup import TransactionGroup
from .util import (TotalsAndBalance, TotalsAndBalancePerProduct,
                   TotalsAndBalancesPerProductType)

# key in session.info dict for information about totals and balances
INFO_CUM_AMOUNTS = 'kneipy_core.AccountCumAmounts'


@enum.unique
class AccountTypes(enum.Enum):
    # ACHTUNG!
    # Änderungen in den möglichen Werten von ENUM-Spalten
    # wie Account.type werden von alembic nicht bemerkt und entsprechend
    # funktioniert das automatische Generieren der Migration nicht.
    # => manuell schreiben
    BalanceSheetOpening = "Saldovorträge"

    Temp = "temporäre Konten"
    Financial = "Finanzkonto"
    Capital = "Kapital"
    PreviousResults = "Vorjahresergebnisse"

    Profits = "Einnahmen"
    Expenses = "Ausgaben"

    FromSales = \
        "Forderungen aus Lieferungen und Leistungen / " + \
        "Verbindlichkeiten aus Lieferungen und Leistungen"
    Transit = "Wechselforderungen / Wechselverbindlichkeiten"
    ConnectedEntities = \
        "Forderungen gegen verbundene Unternehmen" + \
        "Verbindlichkeiten gegen verbundene Unternehmen"
    Others = \
        "Forderungen und sonstige Vermögensgegenstände" + \
        "sonstige Verbindlichkeiten"

    Depreciation = "Abschreibungen"

    Person = "Personenkonten"


class Account(Base, ExternalRefMixin):
    __tablename__ = "account"
    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )

    type = sa.Column(ENUM(AccountTypes), nullable=False)

    balancesheet_id = sa.Column(
        sa.ForeignKey(
            'balancesheet.id',
            onupdate="RESTRICT", ondelete="RESTRICT",
        ),
        nullable=False
    )
    balancesheet = relationship('BalanceSheet', back_populates='accounts')

    parent_id = sa.Column(
        GUID, nullable=True
    )
    parent_type = sa.Column(
        ENUM(AccountTypes), nullable=True
    )

    name = sa.Column(
        sa.Unicode(), nullable=True
    )
    person_id = sa.Column(
        sa.ForeignKey(
            'person.id',
            onupdate="RESTRICT", ondelete="RESTRICT",
        ),
        nullable=True,
    )
    person = relationship('Person', backref="accounts")

    parent = relationship(
        'Account', primaryjoin=(sa.and_(parent_id == id, parent_type == type)),
        remote_side=[id, type],
        back_populates='children',
        uselist=False,
    )
    children = relationship(
        'Account', primaryjoin=(sa.and_(parent_id == id, parent_type == type)),
        remote_side=[parent_id, parent_type],
        back_populates='parent'
    )

    @property
    def totals_and_balances(self):
        if not hasattr(self, '_totals_and_balances'):
            # Cannot be a defaultdict! If it were we'd get zero totals
            # and balances if they're not loaded.
            result = dict()
            try:
                cum_amounts = sa.orm.session.object_session(self).info[INFO_CUM_AMOUNTS][self.id]
            except KeyError:
                return result

            for trx_id, rows in cum_amounts.items():
                result[trx_id] = TotalsAndBalancePerProduct()
                for row in rows.values():
                    result[trx_id][row.product_id] = result[trx_id][row.product_id].add(row)
            self._totals_and_balances = result

        return self._totals_and_balances

    @property
    def totals_and_balance(self):
        if len(self.totals_and_balances) == 1:
            return list(self.totals_and_balances.values())[0]
        else:
            raise ValueError("totals and balances for exactly one transaction id need to be loaded")

    @property
    def cumulative_totals_and_balances(self):
        if not hasattr(self, '_cumulative_totals_and_balances'):
            # for what transaction ids do we know balances for this account
            # and all children?
            transaction_ids = set(self.totals_and_balances.keys())
            for child in self.children:
                transaction_ids.intersection_update(child.cumulative_totals_and_balances.keys())

            res = dict()
            for trx_id in transaction_ids:
                res[trx_id] = TotalsAndBalancePerProduct()
                for child in self.children:
                    ctab = child.cumulative_totals_and_balances[trx_id]
                    for product_id, data in ctab.items():
                        res[trx_id][product_id] = res[trx_id][product_id].add(
                            data
                        )
                for product_id, data in self.totals_and_balances[trx_id].items():
                    res[trx_id][product_id] = res[trx_id][product_id].add(
                        data
                    )
            self._cumulative_totals_and_balances = res
        return self._cumulative_totals_and_balances

    @property
    def cumulative_totals_and_balance(self):
        if len(self.cumulative_totals_and_balances) == 1:
            return list(self.cumulative_totals_and_balances.values())[0]
        else:
            raise ValueError("totals and balances for exactly one transaction id need to be loaded")

    def _invalidate_totals_and_balance_attrs(self):
        if hasattr(self, '_totals_and_balances'):
            del self._totals_and_balances
        if hasattr(self, '_cumulative_totals_and_balances'):
            del self._cumulative_totals_and_balances

    @classmethod
    def load_totals_and_balances(cls, accounts, transaction_ids):
        if isinstance(transaction_ids, int):
            transaction_ids = [transaction_ids]
        if not accounts or not transaction_ids:
            return
        if not isinstance(accounts, list):
            accounts = list(accounts)

        session = sa.orm.session.object_session(accounts[0])
        if INFO_CUM_AMOUNTS not in session.info:
            # cache comulative amounts of accounts
            session.info[INFO_CUM_AMOUNTS] = dict()

            # clear cache
            @sa.event.listens_for(session, "after_commit")
            @sa.event.listens_for(session, "after_rollback")
            def remove_strong_refs(session, *args, **kwargs):
                session.info[INFO_CUM_AMOUNTS] = dict()

        # Query for accounts of different balancesheets seperately.
        # Not doing this will likely result in a suboptimal query plan.
        # Also query in chunks of 500 accounts to account for limitations
        # of the IN sql-construct
        accounts_by_balancesheets = collections.defaultdict(lambda: set())
        for a in accounts:
            accounts_by_balancesheets[a.balancesheet_id].add(a)
        chunks = []
        for accounts_one_balancesheet in accounts_by_balancesheets.values():
            while len(accounts_one_balancesheet) > 500:
                chunks.append([])
                for _ in range(500):
                    chunks[-1].append(accounts_one_balancesheet.pop())
            chunks.append([])
            while accounts_one_balancesheet:
                chunks[-1].append(accounts_one_balancesheet.pop())

        for c in chunks:
            assert c
            # Create dicts in session.info[INFO_CUM_AMOUNTS] as needed. The
            # existence of these dictonaries also signals what's been
            # queried since an account with no transactions will not result
            # in a row in the queries below.
            for a in c:
                if a.id not in session.info[INFO_CUM_AMOUNTS]:
                    session.info[INFO_CUM_AMOUNTS][a.id] = dict()
                for trx_id in transaction_ids:
                    if trx_id not in session.info[INFO_CUM_AMOUNTS][a.id]:
                        session.info[INFO_CUM_AMOUNTS][a.id][trx_id] = dict()

            for t in ["credit", "debit"]:
                q = gen_account_cum_q(t).alias("account_cum_" + t)
                q = sa.select([
                    q.c.balancesheet_id, q.c.transaction_id, q.c.product_id,
                    q.c.account_id, q.c.total_debit, q.c.total_credit, q.c.what
                ]).where(
                    sa.and_(
                        q.c.balancesheet_id == c[0].balancesheet_id,
                        q.c.account_id.in_([a.id for a in c]),
                        q.c.transaction_id.in_(transaction_ids)
                    )
                )
                for r in session.execute(q):
                    session.info[INFO_CUM_AMOUNTS][r.account_id] \
                        [r.transaction_id][(r.product_id, r.what)] = TotalsAndBalance(
                            product_id=r.product_id,
                            total_credit=r.total_credit, total_debit=r.total_debit,
                            balance=r.total_debit - r.total_credit
                        )
        for a in accounts:
            a._invalidate_totals_and_balance_attrs()

    @classmethod
    def load_cumulative_totals_and_balances(cls, accounts, transaction_ids):
        accounts_to_check = set(accounts)
        accounts_including_children = set()
        while accounts_to_check:
            account = accounts_to_check.pop()
            if account in accounts_including_children:
                continue
            for c in account.children:
                accounts_to_check.add(c)
            accounts_including_children.add(account)

        return cls.load_totals_and_balances(accounts_including_children, transaction_ids)


    # NOT NULL / IS NULL prüfen abhängig von der type Spalte
    #
    # ACHTUNG!
    # alembíc revision --autogenerate erkennt Änderungen hier -
    # genauso wie die Assertion im Setup-Code der Tests, die ebenfalls
    # alembic nutzt - NICHT.
    # Deshalb: DRINGEND manuell Migration schreiben bei Änderungen!
    #
    @declared_attr
    def __table_args__(self):
        return tuple(ExternalRefMixin.table_args() + [
            sa.CheckConstraint("""
                (type = 'Person' AND person_id IS NOT NULL AND name IS NULL) OR
                (type = 'Temp'   AND person_id IS NULL     AND name IS NULL) OR
                (type NOT IN ('Person', 'Temp') AND
                    person_id IS NULL AND name IS NOT NULL
                )
            """, name='type_based_null_check'),
            # FIXME: Check the type of the parent account makes sense
            sa.ForeignKeyConstraint(
                [
                    'parent_id',
                    'parent_type',
                ], [
                    'account.id',
                    'account.type'
                ],
                onupdate="RESTRICT", ondelete="RESTRICT",
            ),
            sa.UniqueConstraint(
                'type',
                'id',
            ),
            sa.UniqueConstraint(
                'balancesheet_id', 'id',
                name='uq_account_balancesheet_id_for_fk'
            ),
            sa.UniqueConstraint(
                'balancesheet_id', 'name',
                name='uq_account_balancesheet_id_name'
            )
        ])


def gen_account_cum_q(what):
    assert what in ["debit", "credit"]
    t1 = sa.alias(Transaction, "t1")
    t2 = sa.alias(Transaction, "t2")
    account_c = t2.c.debit_account_id if what == "debit" else t2.c.credit_account_id
    return sa.select([
        t1.c.balancesheet_id,
        t1.c.id.label("transaction_id"),
        t2.c.product_id.label("product_id"),
        account_c.label("account_id"),
        sa.func.sum(t2.c.amount).label("total_" + what),
        sa.literal(0).label("total_" + ("debit" if what == "credit" else "credit")),
        sa.literal('"{}"'.format(what)).label("what")
    ]).select_from(
        sa.join(t1, t2, sa.and_(
            t1.c.balancesheet_id == t2.c.balancesheet_id,
            t2.c.id <= t1.c.id
        ))
    ).group_by(
        t1.c.balancesheet_id, t1.c.id, account_c, t2.c.product_id
    )
