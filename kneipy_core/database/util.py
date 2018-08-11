import uuid
import decimal
import collections

import attr
import sqlalchemy as sa
from sqlalchemy.orm.session import make_transient_to_detached
from sqlalchemy.orm.util import identity_key
from .product import Product


def convert_to_decimal(v):
    if isinstance(v, decimal.Decimal):
        return v
    elif isinstance(v, int):
        return decimal.Decimal(v)
    elif isinstance(v, str):
        return decimal.Decimal(v)
    else:
        raise ValueError('{} could not be converted to decimal.Decimal'.format(type(v)))


@attr.s(slots=True)
class TotalsAndBalance():
    product_id = attr.ib()
    total_credit = attr.ib(converter=convert_to_decimal)
    total_debit = attr.ib(converter=convert_to_decimal)
    balance = attr.ib(converter=convert_to_decimal)
    _product_name = attr.ib(default=None)
    _product = attr.ib(default=None)

    def get_product(self, session):
        if not self._product or self._product not in session.persistent:
            if self._product_name is None:
                # missing info => query db
                self._product = session.query(Product).get(self.product_id)
            else:
                # we have all the info we need => construct an instance
                self._product = Product(id=self.product_id,
                                        name=self._product_name)
                if identity_key(instance=self._product) in session.identity_map or \
                        self._product in session:
                    # This will not result in a query, but return an
                    # instance in the persistent state
                    self._product = session.query(Product).get(self.product_id)
                else:
                    # last resort: Tell SQLAlchemy to assume the instance
                    # we have is persistent in the database
                    make_transient_to_detached(self._product)
                    self._product = session.merge(self._product, load=False)
        return self._product

    def add(self, other):
        assert self.product_id == other.product_id
        if self._product and other._product:
            assert self._product == other._product
        product = self._product if self._product else other._product
        if self._product_name and other._product_name:
            assert self._product_name == other._product_name
        product_name = self._product_name if self._product_name else other._product_name
        return TotalsAndBalance(
            product_id=self.product_id,
            product_name=product_name, product=product,
            total_debit=self.total_debit + other.total_debit,
            total_credit=self.total_credit + other.total_credit,
            balance=self.balance + other.balance,
        )


class TotalsAndBalancePerProduct(collections.UserDict):
    def __missing__(self, key):
        return TotalsAndBalance(
            product_id=key,
            total_credit=0, total_debit=0,
            balance=0
        )


def add_totals_and_balance(a, b):
    return a.add(b)


class TotalsAndBalancesPerProductType(sa.types.TypeDecorator):
    impl = sa.types.JSON

    def process_bind_param(self, value, dialect):
        raise NotImplementedError()

    def process_result_value(self, value, dialect):
        res = TotalsAndBalancePerProduct()
        for product_id, data in value.items():
            for f in ['total_credit', 'total_debit', 'balance']:
                data[f] = decimal.Decimal(data[f])
            res[uuid.UUID(product_id)] = TotalsAndBalance(
                product_id=uuid.UUID(product_id), **data
            )
        return res
