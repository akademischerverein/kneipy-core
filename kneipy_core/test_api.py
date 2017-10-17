import datetime

import nose.tools as n
import sqlalchemy as sa

from . import api, test_util
from .database import Person, Account, Product, \
    AccountPerson, AccountResult, \
    AccountProfits, AccountBalances, \
    AccountExpenses, BalanceSheet, Transaction


class ApiTest(test_util.DbTestCase):
    def create_simple_balance_sheet(self):
        self.balancesheet = BalanceSheet(name='simple test')

        self.accounts = {
            'results': AccountResult(
                balancesheet=self.balancesheet,
                name='Operational Results'
            ),
            'balances': AccountBalances(
                balancesheet=self.balancesheet,
                name='Balances'
            ),
            'johndoe': AccountPerson(
                balancesheet=self.balancesheet,
                person=Person(name='John Doe')
            ),
            'supplier': AccountPerson(
                balancesheet=self.balancesheet,
                person=Person(name='Supplier Inc.')
            )
        }
        self.accounts.update({
            'profits': AccountProfits(
                balancesheet=self.balancesheet,
                parent=self.accounts['results'],
                name='Profits'
            ),
            'expenses': AccountExpenses(
                balancesheet=self.balancesheet,
                parent=self.accounts['results'],
                name='Expenses'
            ),
            'bank': AccountBalances(
                balancesheet=self.balancesheet,
                parent=self.accounts['balances'],
                name='Bank Account'
            ),
            'store': AccountBalances(
                balancesheet=self.balancesheet,
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
        n.eq_(len(self.balancesheet.top_level_accounts), 4)
        n.eq_(len(self.balancesheet.accounts), len(self.accounts))
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
            .filter_by(id=Product.EURO_CT_ID)
            .count(),
            1
        )

    def test_eagerload(self):
        self.create_simple_balance_sheet()
        balances = self.session.query(AccountBalances) \
            .options(
                sa.orm.undefer('totals_and_balance')
            ) \
            .filter_by(name='Balances').one()
        n.eq_(balances, self.accounts['balances'])
        n.eq_(balances.cumulative_totals_and_balance
              [Product.EURO_CT_ID].balance, 0)

        profits = self.session.query(AccountProfits) \
            .options(
                sa.orm.selectinload('children')
            ) \
            .filter_by(name='Profits').one()
        n.eq_(profits, self.accounts['profits'])
        n.eq_(profits.cumulative_totals_and_balance
              [Product.EURO_CT_ID].balance, 0)

    def assert_balancesheet_invariants(self, balancesheet):
        tabs = balancesheet.cumulative_totals_and_balance
        for tab in tabs.values():
            n.eq_(tab.total_debit, tab.total_credit)
            n.eq_(tab.balance, 0)

    def test_simple_transactions(self):
        self.create_simple_balance_sheet()
        self.add_products()

        # Erstmal etwas Inventar einkaufen
        with self.balancesheet.transact_orm(
                text='Accquire stock',
                receiptdate=datetime.datetime.now().date()
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
            # for - let's say - 20€
            t.transaction(
                text='payment',
                credit=self.accounts['expenses'],
                debit=self.accounts['supplier'],
                product=self.session.query(Product)
                .filter_by(id=Product.EURO_CT_ID)
                .one(),
                amount=2000
            )
        self.assert_balancesheet_invariants(self.balancesheet)
        n.eq_(
            self.balancesheet
            .cumulative_totals_and_balance[Product.EURO_CT_ID]
            .total_debit,
            2000
        )
        n.eq_(
            self.balancesheet
            .cumulative_totals_and_balance[self.products['water'].id]
            .total_debit,
            12
        )
        n.eq_(
            self.balancesheet
            .cumulative_totals_and_balance[self.products['beer'].id]
            .total_debit,
            20
        )
        n.eq_(
            self.accounts['supplier']
            .cumulative_totals_and_balance[Product.EURO_CT_ID]
            .total_debit,
            2000
        )
        n.eq_(
            self.accounts['supplier']
            .cumulative_totals_and_balance[self.products['water'].id]
            .total_credit,
            12
        )
        n.eq_(
            self.accounts['supplier']
            .cumulative_totals_and_balance[self.products['beer'].id]
            .total_credit,
            20
        )

        # Ein Bier und ein Wasser an John Doe verkaufen
        # Lass uns außerdem mal das ORM etwas vermeiden
        with self.balancesheet.transact_core(
                text='Accquire stock',
                receiptdate=datetime.datetime.now().date()
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
                .filter_by(id=Product.EURO_CT_ID)
                .one().id,
                amount=200
            )
        self.assert_balancesheet_invariants(self.balancesheet)
        n.eq_(
            self.accounts['store']
            .cumulative_totals_and_balance[Product.EURO_CT_ID]
            .balance,
            0
        )
        n.eq_(
            self.accounts['store']
            .cumulative_totals_and_balance[self.products['beer'].id]
            .balance,
            19
        )
        n.eq_(
            self.accounts['store']
            .cumulative_totals_and_balance[self.products['water'].id]
            .balance,
            11
        )
        # John Doe überweist Geld und bezahlt damit seine Rechnung
        with self.balancesheet.transact_orm(
                text='Payment from John Doe',
                receiptdate=datetime.datetime.now().date()
                ) as t:
            t.transaction(
                text='payment',
                credit=self.accounts['bank'],
                debit=self.accounts['johndoe'],
                product=self.session.query(Product)
                .filter_by(id=Product.EURO_CT_ID)
                .one(),
                amount=200
            )
        self.assert_balancesheet_invariants(self.balancesheet)
        n.eq_(
            self.accounts['johndoe']
            .cumulative_totals_and_balance[Product.EURO_CT_ID]
            .balance,
            0
        )
        n.eq_(
            self.accounts['johndoe']
            .cumulative_totals_and_balance[self.products['beer'].id]
            .balance,
            1
        )
        n.eq_(
            self.accounts['johndoe']
            .cumulative_totals_and_balance[self.products['water'].id]
            .balance,
            1
        )
        n.eq_(
            self.accounts['results']
            .cumulative_totals_and_balance[Product.EURO_CT_ID]
            .balance,
            -1800
        )

        # BalanceAccounts haben umgedrehte Salden. Ein negativer
        # Wert entspricht Guthaben (2€ in diesem Fall)
        n.eq_(
            self.accounts['bank']
            .cumulative_totals_and_balance[Product.EURO_CT_ID]
            .balance,
            -200
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
                receiptdate=datetime.datetime.now().date()
                ) as t:
            t.cancel_transaction(last_transaction, 'ooops')

        n.eq_(
            # self.accounts['bank'] wurde aus der Session geworfen
            # => wird nicht aktualisiert => neu aus db holen
            self.session.query(Account).filter_by(
                id=self.accounts['bank'].id
            ).one()
            .cumulative_totals_and_balance[Product.EURO_CT_ID]
            .balance,
            0
        )
        self.assert_balancesheet_invariants(self.balancesheet)
