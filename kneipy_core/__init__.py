from . import api
from .database import Account, AccountTypes, BalanceSheet, Company, Person, \
    Product, Report, ReportBatch, ReportSequence, ReportTransactions, \
    Transaction, TransactionGroup


def setup_package():
    """module-wide setup for testing"""
    from .test_util import DbTestCase
    DbTestCase.database_setup()
