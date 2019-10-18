import os

import pytest

skip_for_mysql = pytest.mark.skipif(
    os.environ.get('TEST_DATABASE') == 'mysql',
    reason="not supported under MySQL"
)
