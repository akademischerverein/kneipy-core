import uuid
from unittest import TestCase

import nose.tools as n

from .account import \
    TotalsAndBalancesPerProductType


class TotalsAndBalancesPerProductTypeTest(TestCase):
    @n.raises(NotImplementedError)
    def process_bind_param_not_implemented_test(self):
        TotalsAndBalancesPerProductType().process_bind_param(None, None)

    def process_result_value_test(self):
        result_value = {
            'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa': {
                'product_name': 'a',
                'total_credit': 10,
                'total_debit': 20,
                'balance': -10
            },
            'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb': {
                'product_name': 'b',
                'total_credit': 100,
                'total_debit': 200,
                'balance': -100
            }
        }
        r = TotalsAndBalancesPerProductType().process_result_value(
            result_value, None
        )
        n.eq_(r[uuid.UUID(
            'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        )].balance, -10)
        n.eq_(r[uuid.UUID(
            'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
        )].balance, -100)
        n.eq_(len(r), 2)
