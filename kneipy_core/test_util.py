import os
import getpass
import unittest

import alembic
import sqlalchemy as sa
import alembic.config
from alembic.migration import MigrationContext
from alembic.runtime.environment import EnvironmentContext
from alembic.autogenerate import compare_metadata
from alembic.script import ScriptDirectory

from . import database
from .lib.sqlalchemy_session_scope import \
    session_scope


class DbTestCase(unittest.TestCase):
    @classmethod
    def database_setup(cls):
        # Datenbankverbindung herstellen
        database_uri = os.environ.get(
            'DATABASE_URI_TESTS',
            'postgresql://{}@localhost/kneipy-tests'.format(
                getpass.getuser()

            )
        )
        database.connect(database_uri, echo=False)
        assert database.engine.connect()

        # TODO: Sicherstellen, dass dies keine Datenbank mit relevanten Daten ist
        # assert 'test' in URI?

        # Alle Tabellen in der Datenbank entfernen
        meta = sa.MetaData(bind=database.engine)
        meta.reflect()
        meta.drop_all()

        # Alle Tabellen anhand der Migrationen erstellen
        alembic_cfg = alembic.config.Config(
            os.path.join(
                os.path.dirname(__file__),
                '..',
                'alembic.ini'
            ),
            attributes={
                'connectable': database.engine
            }
        )
        alembic.command.upgrade(alembic_cfg, "head")
        ec = EnvironmentContext(
            alembic_cfg,
            ScriptDirectory('migrations')
        )
        ec.configure(
            connection=database.engine.connect(),
            include_object=database.alembic_include_object
        )
        # Weicht das Ergebnis der Migrationen von den
        # Modell-Definitionen ab?
        comparison = compare_metadata(ec.get_context(), database.Base.metadata)
        if comparison:
            raise RuntimeError()

        with session_scope(database.Session()) as s:
            # seed database with essential data
            s.execute(database.Product.insert_currency('EUR'))

    #
    # Das folgende basiert sehr auf
    # http://docs.sqlalchemy.org/en/latest/orm/session_transaction.html
    # Kurz gesagt erlaubt es auch Tests, die .commit() oder .rollback()
    # nutzen, in einer übergeordneten Transaktion laufen zu lassen
    # und anschließend via ROLLBACK alle Änderungen in der Datenbank
    # zu verwerfen.
    #
    def setUp(self):
        # connect to the database
        self.connection = database.engine.connect()

        # begin a non-ORM transaction
        self.trans = self.connection.begin()

        # remove any existing sessions, as they would interfere with
        # us creating a new one with a specified connection
        database.Session.remove()

        if 'QUERY_ECHO' in os.environ:
            database.engine.echo = True

        # bind an individual Session to the connection
        self.session = database.Session(bind=self.connection)

        # start the session in a SAVEPOINT...
        self.session.begin_nested()

        # then each time that SAVEPOINT ends, reopen it
        @sa.event.listens_for(self.session, "after_transaction_end")
        def restart_savepoint(session, transaction):
            if transaction.nested and not transaction._parent.nested:
                # ensure that state is expired the way
                # session.commit() at the top level normally does
                # (optional step)
                session.expire_all()

                session.begin_nested()

    def tearDown(self):
        self.session.close()

        # rollback - everything that happened with the
        # Session above (including calls to commit())
        # is rolled back.
        self.trans.rollback()

        # return connection to the Engine
        self.connection.close()
