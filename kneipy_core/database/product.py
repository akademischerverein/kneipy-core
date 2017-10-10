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

    EURO_CT_ID = uuid.UUID(bytes='€ ct'.encode("utf-8").rjust(16, b'\x00'))

    @classmethod
    def insert_euro_cents(cls):
        insert_stmt = pg_insert(cls.__table__).values(
            id=cls.EURO_CT_ID,
            name='Eurocent'
        )
        return insert_stmt.on_conflict_do_nothing(
            index_elements=['id']
        )
