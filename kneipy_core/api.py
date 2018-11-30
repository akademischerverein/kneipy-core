from contextlib import contextmanager
import sqlalchemy as sa
from .database import Product, Account, \
    TransactionGroup, Transaction, BalanceSheet, Company
import sys
from . import database


class TransactionInterfaceCore():
    def __init__(self, session, transaction_group_id, balancesheet_id):
        self.transaction_group_id = transaction_group_id
        self.balancesheet_id = balancesheet_id
        self.session = session
        self.transactions = []

    def transaction(self, credit_account_id, debit_account_id, product_id,
                    amount, text):
        if amount <= 0:
            raise ValueError(
                'Transaction {} => {} "{}" {} x {} has a non-positive amount'
                .format(
                    credit_account_id, debit_account_id, text,
                    amount, product_id
                )
            )
        assert amount > 0
        self.transactions.append({
            'balancesheet_id': self.balancesheet_id,
            'transaction_group_id': self.transaction_group_id,
            'credit_account_id': credit_account_id,
            'debit_account_id': debit_account_id,
            'product_id': product_id,
            'amount': amount,
            'text': text,
            'cancellation_for_transaction_id': None
        })

    def cancel_transaction(self, transaction_id,
                           credit_account_id, debit_account_id,
                           product_id, original_amount, text):
        assert original_amount > 0
        self.transactions.append({
            'balancesheet_id': self.balancesheet_id,
            'transaction_group_id': self.transaction_group_id,
            'cancellation_for_transaction_id': transaction_id,
            'credit_account_id': credit_account_id,
            'debit_account_id': debit_account_id,
            'product_id': product_id,
            'amount': -original_amount,
            'text': text,
        })

    def tab_orm_invalidate(self, account):
        if hasattr(account, '_transaction_totals'):
            del account._transaction_totals

    def insert(self):
        transaktion_t = Transaction.__table__
        query = transaktion_t.insert() \
            .values(
                transaction_group_id=sa.bindparam('transaction_group_id'),
                credit_account_id=sa.bindparam('credit_account_id'),
                debit_account_id=sa.bindparam('debit_account_id'),
                product_id=sa.bindparam('product_id'),
                amount=sa.bindparam('amount'),
                text=sa.bindparam('text'),
                cancellation_for_transaction_id=sa.bindparam(
                    'cancellation_for_transaction_id'
                )
            )
        self.session.execute(query, self.transactions)
        accounts = set(
            [b['credit_account_id'] for b in self.transactions] +
            [b['debit_account_id'] for b in self.transactions]
        )

        # Dies stellt sicher, dass der Aufruf von identity_key
        # in der Schleife den PK bekommt und somit korrekt
        # geladene Konten gefunden werden, deren Daten eventuell
        # nicht mehr aktuell sind.
        assert len(Account.__table__.primary_key) == 1
        for account_id in accounts:
            identity_key = sa.orm.util.identity_key(
                Account, account_id
            )
            # Konto ist in ORM geladen
            if identity_key in self.session.identity_map:
                # totals_and_balance invalidieren
                # Hat sich durch Transaktionen vermutlich geändert
                self.tab_orm_invalidate(
                    self.session.query(Account).get(account_id)
                )

        self.transactions = []


class TransactionInterfaceORM(TransactionInterfaceCore):
    def __init__(self, transaction_group):
        super().__init__(
            session=sa.orm.object_session(transaction_group),
            transaction_group_id=transaction_group.id,
            balancesheet_id=transaction_group.balancesheet_id
        )

    def transaction(self, credit, debit, product, amount, text):
        assert isinstance(debit, Account)
        assert isinstance(credit, Account)
        assert isinstance(product, Product)

        # Keine Transaktionen über Bilanz (BalanceSheet) Grenzen!
        # Diese würden Invarianten der Bilanz wie "Summe der Haben-Summen
        # aller Konten ist gleich der Summe der Soll-Summen"
        # verletzen.
        assert debit.balancesheet_id == self.balancesheet_id
        assert debit.balancesheet == credit.balancesheet

        return super().transaction(
            credit.id, debit.id,
            product.id, amount,
            text
        )

    def cancel_transaction(self, transaction, text):
        return super().cancel_transaction(
            transaction_id=transaction.id,
            credit_account_id=transaction.credit_account_id,
            debit_account_id=transaction.debit_account_id,
            product_id=transaction.product_id,
            original_amount=transaction.amount,
            text=text
        )


@contextmanager
def transaction_group_orm(balancesheet, text,
                          receiptdate, receipt):
    tg = TransactionGroup(
        balancesheet=balancesheet,
        receiptdate=receiptdate, receipt=receipt,
        text=text
    )
    session = sa.orm.object_session(balancesheet)
    session.add(tg)
    session.flush()

    ts = TransactionInterfaceORM(tg)
    yield ts
    ts.insert()


@contextmanager
def transaction_group_core(session, balancesheet_id, text,
                           receiptdate, receipt):
    transaction_group_t = TransactionGroup.__table__
    insert_q = transaction_group_t.insert() \
        .values(
            balancesheet_id=balancesheet_id,
            receiptdate=receiptdate,
            receipt=receipt,
            text=text
        )
    transaction_group_id = session.execute(insert_q).inserted_primary_key[1]
    ts = TransactionInterfaceCore(
        session,
        transaction_group_id, balancesheet_id
    )
    yield ts
    ts.insert()
