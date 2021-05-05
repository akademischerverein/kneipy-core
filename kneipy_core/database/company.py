import sqlalchemy as sa
from kneipy_core.lib.sqlalchemy_uuid import GUID
from sqlalchemy.orm import relationship

from .base import Base
from .mixins import ExternalRefMixin


class Company(Base, ExternalRefMixin):
    __tablename__ = 'company'

    id = sa.Column(
        GUID,
        primary_key=True,
        server_default=sa.text('gen_random_uuid()')
    )

    name = sa.Column(
        sa.UnicodeText,
        nullable=False,
        unique=True
    )

    top_level_accounts = relationship(
        'Account', primaryjoin=(
            'and_(' +
            '   Account.parent_id.is_(None),' +
            '   Account.company_id == Company.id' +
            ')'
        ),
        overlaps='company',
        lazy=True
    )

    accounts = relationship(
        'Account', back_populates='company',
        overlaps='top_level_accounts'
    )
