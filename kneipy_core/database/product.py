import uuid

import sqlalchemy as sa

from kneipy_core.lib.sqlalchemy_uuid import GUID

from .base import Base
from sqlalchemy.dialects.postgresql import insert as pg_insert


class Product(Base):
    __tablename__ = 'product'
    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )
    name = sa.Column(sa.Unicode, nullable=False)

    @classmethod
    def get_currency_uuid(cls, isocode):
        return uuid.UUID(bytes=isocode.encode("utf-8").rjust(16, b'\x00'))

    @classmethod
    def insert_currency(cls, isocode):
        insert_stmt = pg_insert(cls.__table__).values(
            id=cls.get_currency_uuid(isocode),
            name=isocode
        )
        return insert_stmt.on_conflict_do_nothing(
            index_elements=['id']
        )
