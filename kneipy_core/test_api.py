import datetime
import decimal
from collections import defaultdict

import nose.tools as n
import sqlalchemy as sa

from . import test_util
from .database import (Account, AccountTypes, BalanceSheet, Company, Person,
                       Product, Transaction)


class ApiTest(test_util.DbTestCase):
    def create_simple_balance_sheet(self):
        self.company = Company(name='Test for fun')
        self.balancesheet = BalanceSheet(
            name='simple test',
            company=self.company
        )

        self.accounts = {
            'results': Account(
                type=AccountTypes.PreviousResults,
                company=self.company,
                name='Operational Results'
            ),
            'balances': Account(
                type=AccountTypes.Capital,
                company=self.company,
                name='Balances'
            ),
            'johndoe': Account(
                type=AccountTypes.Person,
                company=self.company,
                person=Person(name='John Doe')
            ),
            'supplier': Account(
                type=AccountTypes.Person,
                company=self.company,
                person=Person(name='Supplier Inc.')
            )
        }
        self.accounts.update({
            'profits': Account(
                type=AccountTypes.Profits,
                company=self.company,
                parent=self.accounts['results'],
                name='Profits'
            ),
            'expenses': Account(
                type=AccountTypes.Profits,
                company=self.company,
                parent=self.accounts['results'],
                name='Expenses'
            ),
            'bank': Account(
                type=AccountTypes.Financial,
                company=self.company,
                parent=self.accounts['balances'],
                name='Bank Account'
            ),
            'store': Account(
                type=AccountTypes.Capital,
                company=self.company,
                parent=self.accounts['balances'],
                name='Inventory of store'
            )
        })
        self.session.add(self.balancesheet)
        for account in self.accounts.values():
            self.session.add(account)
        self.session.commit()

    def test_create_simple_balance_sheet(self):
        self.create_simple_balance_sheet()
        n.eq_(len(self.session.query(Account).all()), len(self.accounts))
        n.eq_(len(self.company.top_level_accounts), 4)
        n.eq_(len(self.company.accounts), len(self.accounts))
        n.eq_(len(self.accounts['results'].children), 2)

    def add_products(self):
        self.products = {
            'beer': Product(name='Beer'),
            'water': Product(name='Water')
        }
        for product in self.products.values():
            self.session.add(product)
        self.session.commit()

    def test_add_products(self):
        self.add_products()
        n.eq_(len(self.session.query(Product).all()), len(self.products) + 1)
        n.eq_(
            self.session.query(Product)
            .filter_by(id=Product.get_currency_uuid('EUR'))
            .count(),
            1
        )

    def test_eagerload(self):
        self.create_simple_balance_sheet()
        account = self.session.query(Account) \
            .options(
                sa.orm.joinedload(Account.company)
            ).filter_by(
                type=AccountTypes.Capital,
                name='Balances') \
            .one()
        Account.load_cumulative_totals_and_balances(
            [account], self.balancesheet.id, self.balancesheet.transaction_id_seq
        )
        n.eq_(account, self.accounts['balances'])
        n.eq_(account.cumulative_totals_and_balance[self.balancesheet.id][self.balancesheet.transaction_id_seq]
              [Product.get_currency_uuid('EUR')].balance, 0)

        profits = self.session.query(Account) \
            .options(
                sa.orm.selectinload('children')
            ) \
            .filter_by(
                name='Profits',
                type=AccountTypes.Profits) \
            .one()
        n.eq_(profits, self.accounts['profits'])
        Account.load_cumulative_totals_and_balances(
            [profits], self.balancesheet.id, self.balancesheet.transaction_id_seq
        )
        n.eq_(profits.cumulative_totals_and_balance[self.balancesheet.id][self.balancesheet.transaction_id_seq]
              [Product.get_currency_uuid('EUR')].balance, 0)
        n.ok_(isinstance(
            profits.cumulative_totals_and_balance[self.balancesheet.id][self.balancesheet.transaction_id_seq]
            [Product.get_currency_uuid('EUR')].balance, decimal.Decimal
        ))

    def assert_balancesheet_invariants(self, balancesheet):
        self.session.refresh(balancesheet)
        trx_id = balancesheet.transaction_id_seq
        balance, total_debit, total_credit = defaultdict(decimal.Decimal), defaultdict(decimal.Decimal), defaultdict(decimal.Decimal)
        Account.load_totals_and_balances(balancesheet.accounts, balancesheet.id, trx_id)
        for a in balancesheet.company.accounts:
            for pid, tab in a.totals_and_balances[balancesheet.id][trx_id].items():
                balance[pid] += tab.balance
                total_debit[pid] += tab.total_debit
                total_credit[pid] += tab.total_credit

        for pid in balance.keys():
            n.eq_(total_debit[pid], total_credit[pid])
            n.eq_(balance[pid], 0)

    def test_simple_transactions(self):
        self.create_simple_balance_sheet()
        self.add_products()

        # Erstmal etwas Inventar einkaufen
        with self.balancesheet.transact_orm(
                text='Accquire stock',
                receiptdate=datetime.datetime.now().date(),
                receipt='BUY-001'
                ) as t:
            t.transaction(
                text='1 case of beer (20 bottles)',
                credit=self.accounts['supplier'],
                debit=self.accounts['store'],
                product=self.products['beer'],
                amount=20
            )
            t.transaction(
                text='2 cases of water (12 bottles)',
                credit=self.accounts['supplier'],
                debit=self.accounts['store'],
                product=self.products['water'],
                amount=12
            )
            # for - let's say - 5,50€
            t.transaction(
                text='payment',
                credit=self.accounts['expenses'],
                debit=self.accounts['supplier'],
                product=self.session.query(Product)
                .filter_by(id=Product.get_currency_uuid('EUR'))
                .one(),
                amount=decimal.Decimal('5.5')
            )
        self.assert_balancesheet_invariants(self.balancesheet)

        n.eq_(
            self.accounts['supplier']
            .cumulative_totals_and_balance[self.balancesheet.id]
            [self.balancesheet.transaction_id_seq]
            [Product.get_currency_uuid('EUR')].total_debit,
            decimal.Decimal('5.5')
        )
        n.eq_(
            self.accounts['supplier']
            .cumulative_totals_and_balance[self.balancesheet.id]
            [self.balancesheet.transaction_id_seq]
            [self.products['water'].id]
            .total_credit,
            12
        )
        n.eq_(
            self.accounts['supplier']
            .cumulative_totals_and_balance[self.balancesheet.id]
            [self.balancesheet.transaction_id_seq]
            [self.products['beer'].id]
            .total_credit,
            20
        )

        # Ein Bier und ein Wasser an John Doe verkaufen
        # Lass uns außerdem mal das ORM etwas vermeiden
        with self.balancesheet.transact_core(
                text='Accquire stock',
                receiptdate=datetime.datetime.now().date(),
                receipt='IN-001'
                ) as t:
            t.transaction(
                text='1 bottle of beer',
                credit_account_id=self.accounts['store'].id,
                debit_account_id=self.accounts['johndoe'].id,
                product_id=self.products['beer'].id,
                amount=1
            )
            t.transaction(
                text='1 bottle of water',
                credit_account_id=self.accounts['store'].id,
                debit_account_id=self.accounts['johndoe'].id,
                product_id=self.products['water'].id,
                amount=1
            )
            # Für 2€
            t.transaction(
                text='payment',
                credit_account_id=self.accounts['johndoe'].id,
                debit_account_id=self.accounts['profits'].id,
                product_id=self.session.query(Product)
                .filter_by(id=Product.get_currency_uuid('EUR'))
                .one().id,
                amount=decimal.Decimal('2.00')
            )
        self.assert_balancesheet_invariants(self.balancesheet)
        trx_id = self.balancesheet.transaction_id_seq
        n.eq_(
            self.accounts['store']
            .cumulative_totals_and_balances[self.balancesheet.id][trx_id][Product.get_currency_uuid('EUR')]
            .balance,
            0
        )
        n.eq_(
            self.accounts['store']
            .cumulative_totals_and_balances[self.balancesheet.id][trx_id][self.products['beer'].id]
            .balance,
            19
        )
        n.eq_(
            self.accounts['store']
            .cumulative_totals_and_balances[self.balancesheet.id][trx_id][self.products['water'].id]
            .balance,
            11
        )
        # John Doe überweist Geld und bezahlt damit seine Rechnung
        with self.balancesheet.transact_orm(
                text='Payment from John Doe',
                receiptdate=datetime.datetime.now().date(),
                receipt='SELL-001'
                ) as t:
            t.transaction(
                text='payment',
                credit=self.accounts['bank'],
                debit=self.accounts['johndoe'],
                product=self.session.query(Product)
                .filter_by(id=Product.get_currency_uuid('EUR'))
                .one(),
                amount=decimal.Decimal('2.00')
            )
        self.assert_balancesheet_invariants(self.balancesheet)
        trx_id = self.balancesheet.transaction_id_seq
        n.eq_(
            self.accounts['johndoe']
            .cumulative_totals_and_balances[self.balancesheet.id][trx_id][Product.get_currency_uuid('EUR')]
            .balance,
            0
        )
        n.eq_(
            self.accounts['johndoe']
            .cumulative_totals_and_balances[self.balancesheet.id][trx_id][self.products['beer'].id]
            .balance,
            1
        )
        n.eq_(
            self.accounts['johndoe']
            .cumulative_totals_and_balances[self.balancesheet.id][trx_id][self.products['water'].id]
            .balance,
            1
        )
        n.eq_(
            self.accounts['results']
            .cumulative_totals_and_balances[self.balancesheet.id][trx_id][Product.get_currency_uuid('EUR')]
            .balance,
            decimal.Decimal('-3.5')
        )

        # BalanceAccounts haben umgedrehte Salden. Ein negativer
        # Wert entspricht Guthaben (2€ in diesem Fall)
        n.eq_(
            self.accounts['bank']
            .cumulative_totals_and_balances[self.balancesheet.id][trx_id][Product.get_currency_uuid('EUR')]
            .balance,
            decimal.Decimal('-2')
        )

        # Alle ORM instancen aus der Session entfernen
        # => self.balancesheet und self.accounts funktionieren nicht mehr!
        self.session.expunge_all()

        # letzte Buchung stornieren
        last_transaction = self.session.query(Transaction) \
            .order_by(sa.desc(Transaction.id)) \
            .limit(1) \
            .one()
        # Bilanz wieder holen
        self.balancesheet = last_transaction.balancesheet

        with self.balancesheet.transact_orm(
                text='Cancellation',
                receiptdate=datetime.datetime.now().date(),
                receipt='CANCEL-001'
                ) as t:
            t.cancel_transaction(last_transaction, 'ooops')


        self.assert_balancesheet_invariants(self.balancesheet)
        trx_id = self.balancesheet.transaction_id_seq
        n.eq_(
            # self.accounts['bank'] wurde aus der Session geworfen
            # => wird nicht aktualisiert => neu aus db holen
            self.session.query(Account).filter_by(
                id=self.accounts['bank'].id
            ).one()
            .cumulative_totals_and_balances[self.balancesheet.id][trx_id][Product.get_currency_uuid('EUR')]
            .balance,
            0
        )

    def test_sum_with_transactions_in_self_and_children(self):
        self.create_simple_balance_sheet()

        with self.balancesheet.transact_core(
                text='Sell stuff',
                receiptdate=datetime.datetime.now().date(),
                receipt='IN-001'
                ) as t:
            t.transaction(
                text='Sold whatever',
                credit_account_id=self.accounts['johndoe'].id,
                debit_account_id=self.accounts['profits'].id,
                product_id=self.session.query(Product)
                .filter_by(id=Product.get_currency_uuid('EUR'))
                .one().id,
                amount=decimal.Decimal('5.15')
            )
        with self.balancesheet.transact_core(
                text='year end',
                receiptdate=datetime.datetime.now().date(),
                receipt='IN-001'
                ) as t:
            t.transaction(
                text='close profits',
                credit_account_id=self.accounts['profits'].id,
                debit_account_id=self.accounts['results'].id,
                product_id=self.session.query(Product)
                .filter_by(id=Product.get_currency_uuid('EUR'))
                .one().id,
                amount=decimal.Decimal('5.15')
            )
        self.session.refresh(self.balancesheet)
        Account.load_cumulative_totals_and_balances(
            [self.accounts["results"]], self.balancesheet.id, [self.balancesheet.transaction_id_seq]
        )
        ctab = self.accounts['results'].cumulative_totals_and_balances[self.balancesheet.id][self.balancesheet.transaction_id_seq]
        n.eq_(ctab[Product.get_currency_uuid('EUR')].total_credit, decimal.Decimal('5.15'))
        n.eq_(ctab[Product.get_currency_uuid('EUR')].total_debit, decimal.Decimal('10.30'))
        n.eq_(ctab[Product.get_currency_uuid('EUR')].balance, decimal.Decimal('5.15'))

    def test_get_product(self):
        self.create_simple_balance_sheet()
        self.add_products()

        # Erstmal etwas Inventar einkaufen
        with self.balancesheet.transact_orm(
                text='Accquire stock',
                receiptdate=datetime.datetime.now().date(),
                receipt='BUY-001'
                ) as t:
            t.transaction(
                text='1 case of beer (20 bottles)',
                credit=self.accounts['supplier'],
                debit=self.accounts['store'],
                product=self.products['beer'],
                amount=20
            )
            t.transaction(
                text='payment',
                credit=self.accounts['expenses'],
                debit=self.accounts['supplier'],
                product=self.session.query(Product)
                .filter_by(id=Product.get_currency_uuid('EUR'))
                .one(),
                amount=decimal.Decimal('5.5')
            )
        self.assert_balancesheet_invariants(self.balancesheet)
        n.eq_(
            self.accounts['supplier']
            .cumulative_totals_and_balance[self.balancesheet.id][self.balancesheet.transaction_id_seq][Product.get_currency_uuid('EUR')]
            .get_product(self.session),
            self.session.query(Product).get(Product.get_currency_uuid('EUR'))
        )
        n.eq_(
            self.accounts['supplier']
            .cumulative_totals_and_balance[self.balancesheet.id][self.balancesheet.transaction_id_seq][self.products['beer'].id]
            .get_product(self.session),
            self.products['beer']
        )

    @n.raises(ValueError)
    def test_invalid_transaction_negative_amount(self):
        self.create_simple_balance_sheet()
        with self.balancesheet.transact_orm(
                text='test',
                receiptdate=datetime.datetime.now().date(),
                receipt='TEST-001') as t:
            t.transaction(
                text='invalid',
                credit=self.accounts['bank'],
                debit=self.accounts['johndoe'],
                product=self.session.query(Product)
                .filter_by(id=Product.get_currency_uuid('EUR'))
                .one(),
                amount=decimal.Decimal('-20')
            )

    @n.raises(sa.exc.IntegrityError)
    def test_invalid_transaction_same_accounts(self):
        self.create_simple_balance_sheet()
        with self.balancesheet.transact_orm(
                text='test',
                receiptdate=datetime.datetime.now().date(),
                receipt='TEST-002') as t:
            t.transaction(
                text='invalid',
                credit=self.accounts['bank'],
                debit=self.accounts['bank'],
                product=self.session.query(Product)
                .filter_by(id=Product.get_currency_uuid('EUR'))
                .one(),
                amount=decimal.Decimal('20')
            )
