import inspect
import re


def get_formatted_function_signature(func):
    signature = str(inspect.signature(func))
    return re.sub('self(, )?', '', signature).replace('()', '( )')
