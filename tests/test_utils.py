import pytest
from difonlib.utils import logdbg


@pytest.mark.slow
def test_log_dbg():
    logdbg("hello 12345")
    assert True
