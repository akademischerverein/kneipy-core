import datetime

import nose.tools as n
import sqlalchemy as sa

from . import api, test_util
from .database import Base


class ApiTest(test_util.DbTestCase):
    def test_check_constraints(self):
        rows = self.session.execute("""
        SELECT constraint_name FROM information_schema.check_constraints WHERE
        constraint_schema = 'public'
        """).fetchall()
        db_ck = dict((r[0], False) for r in rows)

        for table in Base.metadata.sorted_tables:
            for constraint in table.constraints:
                if not isinstance(constraint, sa.CheckConstraint):
                    continue
                if constraint._type_bound:
                    continue

                n.ok_(
                    constraint.name in db_ck,
                    'check constraint {} not found in db'.format(
                        constraint.name
                    )
                )
                n.ok_(
                    not db_ck[constraint.name],
                    'check constraint {} found twice in model'.format(
                        constraint.name
                    )
                )
                db_ck[constraint.name] = True

        for name, found in db_ck.items():
            if not name.startswith('ck_'):
                # does not follow naming schema => ignore
                continue
            n.ok_(found, 'check constraint {} not found in model'.format(name))

