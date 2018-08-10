import sqlalchemy as sa
from sqlalchemy.orm import relationship

from .base import Base
from .mixins import ExternalRefMixin


class Company(Base, ExternalRefMixin):
    __tablename__ = 'company'

    id = sa.Column(
        sa.BigInteger,
        primary_key=True,
        autoincrement=True
    )

    # FIXME: Das hier benötigt PostgreSQL 10:
    #
    #id = sa.Column(
    #    GUID,
    #    primary_key=True,
    #    server_default=sa.text('gen_random_uuid()')
    #)

    name = sa.Column(
        sa.UnicodeText,
        nullable=False,
        unique=True
    )
