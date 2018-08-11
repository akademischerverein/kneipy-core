import uuid
import decimal
import collections

import sqlalchemy as sa

TotalsAndBalance = collections.namedtuple(
    'TotalsAndBalance',
    'product_id total_credit total_debit balance'.split()
)


class TotalsAndBalancePerProduct(collections.UserDict):
    def __missing__(self, key):
        return TotalsAndBalance(
            product_id=key,
            total_credit=decimal.Decimal(0), total_debit=decimal.Decimal(0),
            balance=decimal.Decimal(0)
        )


def add_totals_and_balance(a, b):
    assert a.product_id == b.product_id
    return TotalsAndBalance(
        product_id=a.product_id,
        total_debit=a.total_debit + b.total_debit,
        total_credit=a.total_credit + b.total_credit,
        balance=a.balance + b.balance
    )


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
