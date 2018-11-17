import enum

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import \
    declared_attr
from sqlalchemy.dialects.postgresql import ENUM

from kneipy_core.lib.sqlalchemy_uuid import GUID

from .base import Base
from .util import TotalsAndBalancePerProduct, \
    TotalsAndBalancesPerProductType, \
    add_totals_and_balance
from .mixins import ExternalRefMixin
from .product import Product
from .transaction import SA_AMOUNT_TYPE, \
    Transaction
from .transactiongroup import TransactionGroup
from .balancesheet import BalanceSheet


def totals_and_balances_query(id_column):
    d_zero = sa.cast(0, SA_AMOUNT_TYPE)
    return sa.select([
        sa.type_coerce(
            sa.func.coalesce(
                sa.func.json_object_agg(
                    sa.column('product_id'), sa.column('data')
                ),
                sa.func.json_build_object()
            ),
            TotalsAndBalancesPerProductType()
        )
    ]).select_from(
        sa.select([
            Product.id.label('product_id'),
            sa.func.json_build_object(
                sa.literal('product_name'),
                sa.literal_column('Product.name'),
                sa.literal('total_debit'),
                sa.cast(
                    sa.func.coalesce(sa.column('total_debit'), d_zero),
                    sa.Text
                ),
                sa.literal('total_credit'),
                sa.cast(
                    sa.func.coalesce(sa.column('total_credit'), d_zero),
                    sa.Text
                ),
                sa.literal('balance'),
                sa.cast(
                    sa.func.coalesce(sa.column('total_debit'), d_zero) -
                    sa.func.coalesce(sa.column('total_credit'), d_zero),
                    sa.Text
                )
            ).label('data')
        ]).select_from(
            sa.outerjoin(
                # TODO: Product muss hier eigentlich nicht vorkommen
                Product,
                sa.select([
                    Transaction.debit_account_id.label('account_id'),
                    Transaction.product_id.label('product_id'),
                    sa.func.sum(Transaction.amount).label('total_debit'),
                ]).group_by(
                    Transaction.debit_account_id,
                    Transaction.product_id
                ).alias('total_debit'),
                sa.and_(
                    sa.literal_column('total_debit.product_id') == Product.id,
                    sa.literal_column('total_debit.Account_id') == id_column
                )
            ).outerjoin(
                sa.select([
                    Transaction.credit_account_id.label('account_id'),
                    Transaction.product_id.label('product_id'),
                    sa.func.sum(Transaction.amount).label('total_credit'),
                ]).group_by(
                    Transaction.credit_account_id,
                    Transaction.product_id
                ).alias('total_credit'),
                sa.and_(
                    sa.literal_column('total_credit.product_id') == Product.id,
                    sa.literal_column('total_credit.Account_id') == id_column
                )
            )
        ).where(
            sa.or_(
                sa.column("total_debit").isnot(None),
                sa.column("total_credit").isnot(None)
            )
        ).alias('totals_and_balances_per_product')
    )


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

    totals_and_balance = sa.orm.column_property(
        totals_and_balances_query(
            id  # Account.id
        ), deferred=True
    )

    @property
    def cumulative_totals_and_balance(self):
        res = TotalsAndBalancePerProduct()
        # 10 Ebenen des Konten-Baumes laden mit einem Query pro Ebene
        # Kostet leider einen zusätzlich, da die aktuelle Instanz
        # erneut geladen wird
        instance_state = sa.inspect(self)
        lazy_fields = 'children totals_and_balance'.split()
        if any(f in instance_state.unloaded for f in lazy_fields):
            # eager load 10 Ebenen, inkl. der Summen und Salden
            query_options = sa.orm
            if 'totals_and_balance' in instance_state.unloaded:
                query_options = query_options.undefer('totals_and_balance')
            for _ in range(10):
                query_options = query_options \
                    .selectinload('children')\
                    .undefer('totals_and_balance')

            instance_state.session.query(self.__class__) \
                .options(query_options) \
                .filter_by(id=self.id).all()

        for child in self.children:
            ctab = child.cumulative_totals_and_balance
            for product_id, data in ctab.items():
                if product_id not in res:
                    res[product_id] = data
                else:
                    res[product_id] = add_totals_and_balance(
                        res[product_id], data
                    )
        for product_id, data in self.totals_and_balance.items():
            if product_id not in res:
                res[product_id] = data
            else:
                res[product_id] = add_totals_and_balance(
                    res[product_id], data
                )
        return res

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


def gen_account_cum_q(debit):
    t1 = sa.alias(Transaction, "t1")
    t2 = sa.alias(Transaction, "t2")
    debit_c = t2.c.debit_account_id if debit else t2.c.credit_account_id
    return sa.select([
        t1.c.balancesheet_id,
        t1.c.id.label("transaction_id"),
        t1.c.product_id.label("product_id"),
        debit_c.label("account_id"),
        sa.func.sum(t2.c.amount).label("amount")
    ]).select_from(
        sa.join(t1, t2, sa.and_(
            t1.c.balancesheet_id == t2.c.balancesheet_id,
            t2.c.id <= t1.c.id
        ))
    ).group_by(
        t1.c.balancesheet_id, t1.c.id, debit_c, t1.c.product_id
    )

class AccountCumCredit(Base):
    __table__ = gen_account_cum_q(False).alias("account_cum_credit")
    __mapper_args__ = {
        'primary_key':[__table__.c.balancesheet_id, __table__.c.account_id, __table__.c.transaction_id,  __table__.c.product_id]
    }

    @property
    def dict_key(self):
        return (self.product_id, self.transaction_id)


class AccountCumDebit(Base):
    __table__ = gen_account_cum_q(True).alias("account_cum_debit")
    __mapper_args__ = {
        'primary_key':[__table__.c.balancesheet_id, __table__.c.account_id, __table__.c.transaction_id,  __table__.c.product_id]
    }

    @property
    def dict_key(self):
        return (self.product_id, self.transaction_id)


Account.cum_credit = relationship(
    "AccountCumCredit",
    primaryjoin=(
        "and_(" +
        "    Account.id == AccountCumCredit.account_id," +
        "    Account.balancesheet_id == AccountCumCredit.balancesheet_id" +
        ")"
    ),
    foreign_keys=[Account.balancesheet_id, Account.id],
    uselist=True,
    collection_class=sa.orm.collections.attribute_mapped_collection("dict_key"),
    viewonly=True
)
Account.cum_debit = relationship(
    "AccountCumDebit",
    primaryjoin=(
        "and_(" +
        "    Account.id == AccountCumDebit.account_id," +
        "    Account.balancesheet_id == AccountCumDebit.balancesheet_id" +
        ")"
    ),
    foreign_keys=[Account.balancesheet_id, Account.id],
    uselist=True,
    collection_class=sa.orm.collections.attribute_mapped_collection("dict_key"),
    viewonly=True
)
