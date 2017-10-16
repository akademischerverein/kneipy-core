import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.scoping import scoped_session

from .base import Base
from .person import Person
from .account import Account, AccountTemp, \
    AccountPerson, AccountResult, \
    AccountProfits, AccountBalances, \
    AccountExpenses
from .product import Product
from .transaction import Transaction
from .balancesheet import BalanceSheet
from .transactiongroup import TransactionGroup

Session = None
engine = None


def connect(uri, **kw):
    global Session
    global engine
    assert engine is None
    assert Session is None
    engine = sa.create_engine(
        uri,
        isolation_level='SERIALIZABLE',
        **kw)
    Session = scoped_session(sessionmaker(bind=engine))


__all__ = [
    'Base', 'Session', 'engine', 'connect',
    'Person', 'Account', 'AccountTemp',
    'AccountPerson', 'AccountResult',
    'AccountProfits', 'AccountBalances',
    'AccountExpenses', 'AccountBalanceSheet',
    'Product', 'BalanceSheet',
    'Transaction', 'TransactionGroup'
]
