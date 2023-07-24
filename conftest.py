# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from doctest import ELLIPSIS

import pytest

from sybil import Sybil
from sybil.parsers.rest import DocTestParser, PythonCodeBlockParser

import svcs


pytest_collect_file = Sybil(
    parsers=[
        DocTestParser(optionflags=ELLIPSIS),
        PythonCodeBlockParser(),
    ],
    patterns=["*.md", "*.py"],
).pytest()


@pytest.fixture(name="registry")
def _registry():
    return svcs.Registry()


@pytest.fixture(name="container")
def _container(registry):
    return svcs.Container(registry)
