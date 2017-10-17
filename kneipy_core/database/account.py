import enum

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import \
    declared_attr
from sqlalchemy.dialects.postgresql import ENUM

from kneipy_core.lib.sqlalchemy_uuid import GUID

from .base import Base
from .util import TotalsAndBalancesPerProductType, \
    add_totals_and_balance
from .mixins import ExternalRefMixin
from .product import Product
from .transaction import Transaction


def totals_and_balances_query(id_column):
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
                sa.literal('product_name'), Product.name,
                sa.literal('total_debit'),
                sa.func.coalesce(sa.column('total_debit'), 0),
                sa.literal('total_credit'),
                sa.func.coalesce(sa.column('total_credit'), 0),
                sa.literal('balance'),
                sa.func.coalesce(sa.column('total_debit'), 0) -
                sa.func.coalesce(sa.column('total_credit'), 0),
            ).label('data')
        ]).select_from(
            sa.outerjoin(
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
                sa.column("total_credit").isnot(None),
                Product.id == Product.EURO_CT_ID
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
    BalanceSheetOpening = 1
    Temp = 10
    Person = 20
    Result = 30
    Profits = 31
    Expenses = 32
    Balances = 40


class Account(Base, ExternalRefMixin):
    __tablename__ = "account"
    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )

    type = sa.Column(ENUM(AccountTypes), nullable=False)

    balancesheet_id = sa.Column(sa.ForeignKey('balancesheet.id'))
    balancesheet = relationship('BalanceSheet', back_populates='accounts')

    parent_id = sa.Column(
        GUID, nullable=True
    )
    parent_type = sa.Column(
        ENUM(AccountTypes), nullable=True
    )

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
        res = {}
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
                # FIXME: Diese Schleife sollte nicht sein
                for k in 'total_debit total_credit balance'.split():
                    res[product_id] = add_totals_and_balance(
                        res[product_id], data
                    )
        return res

    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": "impossible",
        "with_polymorphic": "*",  # Spalten aller Kind-Klassen ebenfalls
                                  # laden

    }

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
        (type = 'Temp'     AND person_id IS NULL     AND name IS NULL    ) OR
        (type = 'Person'   AND person_id IS NOT NULL AND name IS NULL    ) OR
        (type IN ('Balances', 'Result', 'Profits', 'Expenses') AND
            person_id IS NULL AND name IS NOT NULL
        )
            """, name='type_based_null_check'),
            sa.CheckConstraint("""
            (
                (type IN (
                    'Person', 'Result',
                    'Balances', 'Temp',
                    'BalanceSheetOpening')
                ) AND
                (parent_type IS NULL)
            ) OR (
                type = parent_type AND type IS NOT NULL
            ) OR (
                type IN ('Profits', 'Expenses') AND parent_type = 'Result'
            )
            """, name='parent_type_check'),
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
                'balancesheet_id', 'id'
            )
        ])


class AccountTemp(Account):
    __mapper_args__ = {'polymorphic_identity': AccountTypes.Temp}


class AccountPerson(Account):
    __mapper_args__ = {'polymorphic_identity': AccountTypes.Person}

    person_id = sa.Column(
        sa.ForeignKey('person.id', onupdate="RESTRICT", ondelete="RESTRICT")
    )
    person = relationship('Person', backref="konten")


class AccountNameMixin():
    @declared_attr
    def name(self):
        "name column, if not present already."
        return Account.__table__.c.get(
            'name',
            sa.Column(sa.Unicode, nullable=True)
        )


class AccountBalances(Account, AccountNameMixin):
    __mapper_args__ = {'polymorphic_identity': AccountTypes.Balances}
    # name Spalte aus AccountNameMixin


class AccountResult(Account, AccountNameMixin):
    __mapper_args__ = {'polymorphic_identity': AccountTypes.Result}
    # name Spalte aus AccountNameMixin


class AccountProfits(Account, AccountNameMixin):
    __mapper_args__ = {'polymorphic_identity': AccountTypes.Profits}
    # name Spalte aus AccountNameMixin


class AccountExpenses(Account, AccountNameMixin):
    __mapper_args__ = {'polymorphic_identity': AccountTypes.Expenses}
    # name Spalte aus AccountNameMixin
