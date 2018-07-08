from . import api


def setup_package():
    """module-wide setup for testing"""
    from .test_util import DbTestCase
    DbTestCase.database_setup()
