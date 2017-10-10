from unittest import TestCase
from sqlalchemy.dialects import postgresql, sqlite
from .sqlalchemy_uuid import GUID
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.types import CHAR

class SQLAlchemyUUIDTest(TestCase):
    def test_postgresql(self):
        guid = GUID()
        assert isinstance(
            guid.load_dialect_impl(postgresql.base.dialect()),
            UUID
        )
        assert guid.process_bind_param(
            None,
            postgresql.base.dialect()
        ) is None
        test_uuid = uuid.UUID(bytes=b'test'.rjust(16, b'\x00'))
        assert guid.process_bind_param(
            test_uuid,
            postgresql.base.dialect()
        ) == str(test_uuid)

    def test_sqlite(self):
        guid = GUID()
        assert isinstance(
            guid.load_dialect_impl(sqlite.dialect()),
            CHAR
        )
        assert guid.process_bind_param(
            None,
            sqlite.dialect()
        ) is None
        test_uuid = uuid.UUID(bytes=b'test'.rjust(16, b'\x00'))
        assert guid.process_bind_param(
            test_uuid,
            sqlite.dialect()
        ) == '00000000000000000000000074657374'
        assert guid.process_bind_param(
            str(test_uuid),
            sqlite.dialect()
        ) == '00000000000000000000000074657374'
