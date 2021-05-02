import inspect
import os
import sys

import pytest

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from statsd_asgi.utils import get_metric_name_base


def test_get_metric_name_base():
    assert (
        get_metric_name_base("testservice", "http://mysuperawesomeapi.biz/api/v1/foo")
        == "testservice.api.v1.foo"
    )
