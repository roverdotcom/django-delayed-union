import inspect
import re

from future.utils import PY2


def get_formatted_function_signature(func):
    if PY2:
        signature = inspect.formatargspec(*inspect.getargspec(func))
    else:
        signature = inspect.formatargspec(*inspect.getfullargspec(func))
    return re.sub('self(, )?', '', signature).replace('()', '( )')
