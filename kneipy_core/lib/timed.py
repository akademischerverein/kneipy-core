from datetime import datetime
from contextlib import contextmanager
import sys


@contextmanager
def timed(msg='', print_to=sys.stderr):
    start = datetime.now()
    yield
    end = datetime.now()
    print('{}: {:.3f}s'.format(
        msg,
        (end - start).total_seconds()
    ), file=print_to)
