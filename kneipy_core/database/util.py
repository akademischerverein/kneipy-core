import uuid
import decimal
import collections

import sqlalchemy as sa

TotalsAndBalance = collections.namedtuple(
    'TotalsAndBalance',
    'product_name total_credit total_debit balance'.split()
)


def add_totals_and_balance(a, b):
    assert a.product_name == b.product_name
    return TotalsAndBalance(
        product_name=a.product_name,
        total_debit=a.total_debit + b.total_debit,
        total_credit=a.total_credit + b.total_credit,
        balance=a.balance + b.balance
    )


class TotalsAndBalancesPerProductType(sa.types.TypeDecorator):
    impl = sa.types.JSON

    def process_bind_param(self, value, dialect):
        raise NotImplementedError()

    def process_result_value(self, value, dialect):
        res = {}
        for product_id, data in value.items():
            for f in ['total_credit', 'total_debit', 'balance']:
                data[f] = decimal.Decimal(data[f])
            res[uuid.UUID(product_id)] = TotalsAndBalance(**data)
        return res
