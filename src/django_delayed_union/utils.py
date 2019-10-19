import inspect
import re


def get_formatted_function_signature(func):
    signature = inspect.formatargspec(*inspect.getfullargspec(func))
    return re.sub('self(, )?', '', signature).replace('()', '( )')
