import sqlalchemy as sa
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import HSTORE


class ExternalRefMixin():
    external_refs = sa.Column(
        MutableDict.as_mutable(
            HSTORE(text_type=sa.Text)
        ),
        nullable=True,
    )

    @classmethod
    def table_args(cls):
        return [sa.CheckConstraint(
            '''
                (external_refs IS NULL) OR
                (array_length(akeys(external_refs), 1) > 0)
            ''', name='external_refs_null_or_used'
        )]
