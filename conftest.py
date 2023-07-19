from doctest import ELLIPSIS

import pytest

from sybil import Sybil
from sybil.parsers.rest import DocTestParser, PythonCodeBlockParser

import svc_reg


pytest_collect_file = Sybil(
    parsers=[
        DocTestParser(optionflags=ELLIPSIS),
        PythonCodeBlockParser(),
    ],
    patterns=["*.md", "*.py"],
).pytest()


@pytest.fixture(name="registry")
def _registry():
    return svc_reg.Registry()


@pytest.fixture(name="container")
def _container(registry):
    return svc_reg.Container(registry)
