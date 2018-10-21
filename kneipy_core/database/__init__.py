import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.scoping import scoped_session

from .base import Base
from .person import Person
from .account import Account, AccountTypes
from .company import Company
from .product import Product
from .report import Report, ReportBatch, ReportSequence, ReportTransactions
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


def alembic_include_object(o, name, type_, reflected, compare_to):
    # Dieser Index gehört zu einem Exclusion-Constraint, den alembic
    # nicht korrekt erkennt und daher entfernen will. => ignorieren
    if name == 'ex_balancesheet_company_id_daterange':
        return False
    return True


__all__ = [
    'Base', 'Session', 'engine', 'connect',
    'Person', 'Account', 'AccountTypes',
    'AccountBalanceSheet',
    'Product', 'BalanceSheet',
    'Transaction', 'TransactionGroup'
]
