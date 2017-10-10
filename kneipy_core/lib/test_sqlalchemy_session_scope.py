from contextlib import suppress
import nose.tools as n
from unittest import TestCase
from .. import test_util, database
from .sqlalchemy_session_scope import session_scope


class SessionScopeTest(TestCase):
    def setUp(self):
        self.session = database.Session()
        self.session.execute('''
        DROP TABLE IF EXISTS test_session_scope
        ''')
        self.session.commit()

    def tearDown(self):
        self.session.execute('''
        DROP TABLE IF EXISTS test_session_scope
        ''')
        self.session.commit()

    def test_commit(self):
        with session_scope(self.session) as s:
            s.execute('''
                CREATE TABLE test_session_scope(
                    id SERIAL,
                    text TEXT NOT NULL
                );
                INSERT INTO test_session_scope (text)
                VALUES ('hello'), ('world');
            ''')
        rows = s.execute('SELECT COUNT(*) FROM test_session_scope')
        assert rows.fetchall()[0][0] == 2

    def test_rollback(self):
        with session_scope(self.session) as s:
            s.execute('''
                CREATE TABLE test_session_scope(
                    id SERIAL,
                    text TEXT NOT NULL
                );
                INSERT INTO test_session_scope (text)
                VALUES ('hello'), ('world');
            ''')

        with suppress(RuntimeError):
            with session_scope(self.session) as s:
                s.execute('''
                INSERT INTO test_session_scope (text)
                VALUES ('good'), ('bye');
                ''')
                raise RuntimeError('OOOOps')
        rows = s.execute('SELECT COUNT(*) FROM test_session_scope')
        assert rows.fetchall()[0][0] == 2