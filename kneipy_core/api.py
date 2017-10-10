from contextlib import contextmanager
import sqlalchemy as sa
from .database import Product, Account, \
    TransactionGroup, Transaction


class TransactionInterface():
    def __init__(self, transaction_group):
        self.transaction_group = transaction_group
        self.transactions = []

    def transaction(self, credit, debit, product, amount, text):
        assert isinstance(debit, Account)
        assert isinstance(credit, Account)
        assert isinstance(product, Product)
        assert amount > 0
        # no Transactions across balance sheet boundaries
        # doing so would break invariants like cummulative balance
        # of all accounts is zero.
        assert debit.balancesheet == credit.balancesheet
        self.transactions.append({
            'credit': credit, 'debit': debit,
            'product': product, 'amount': amount,
            'text': text
        })

    def tab_invalidate(self, session, account):
        instance_state = sa.inspect(account)
        if 'totals_and_balance' not in instance_state.unloaded:
            session.expire(
                account, ['totals_and_balance']
            )
        if account.parent:
            self.tab_invalidate(session, account.parent)

    def insert(self, session):
        transaktion_t = Transaction.__table__
        query = transaktion_t.insert() \
            .values(
                transaction_group_id=sa.bindparam('transaction_group_id'),
                credit_account_id=sa.bindparam('credit_account_id'),
                debit_account_id=sa.bindparam('debit_account_id'),
                product_id=sa.bindparam('product_id'),
                amount=sa.bindparam('amount'),
                text=sa.bindparam('text')
            )
        session.execute(query, [
            {
                'transaction_group_id': self.transaction_group.id,
                'credit_account_id': b['credit'].id,
                'debit_account_id': b['debit'].id,
                'product_id': b['product'].id,
                'amount': b['amount'],
                'text': b['text']
            } for b in self.transactions
        ])
        konten = set(
            [b['debit'] for b in self.transactions] +
            [b['credit'] for b in self.transactions]
        )
        for account in konten:
            self.tab_invalidate(session, account)
        self.transactions = []


@contextmanager
def transaction_group(session, text, receiptdate, receipt=None):
    tg = TransactionGroup(
        receiptdate=receiptdate, receipt=receipt,
        text=text
    )
    session.add(tg)
    session.flush()

    ts = TransactionInterface(tg)
    yield ts
    ts.insert(session)
