import sqlalchemy as sa

from kneipy_core.lib.sqlalchemy_uuid import GUID

from .base import Base


class Person(Base):
    __tablename__ = 'person'
    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )
    name = sa.Column(sa.Unicode, nullable=False)
