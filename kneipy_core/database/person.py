import sqlalchemy as sa
from sqlalchemy.ext.declarative import \
    declared_attr

from kneipy_core.lib.sqlalchemy_uuid import GUID

from .base import Base
from .mixins import ExternalRefMixin


class Person(Base, ExternalRefMixin):
    __tablename__ = 'person'
    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )
    name = sa.Column(sa.Unicode, nullable=False)

    @declared_attr
    def __table_args__(self):
        return tuple(ExternalRefMixin.table_args())
