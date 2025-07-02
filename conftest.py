# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import importlib

from doctest import ELLIPSIS

import pytest

from sybil import Sybil
from sybil.parsers import myst, rest

import svcs

from tests.helpers import CloseMe
from tests.ifaces import Service


markdown_examples = Sybil(
    parsers=[
        myst.DocTestDirectiveParser(optionflags=ELLIPSIS),
        myst.PythonCodeBlockParser(doctest_optionflags=ELLIPSIS),
        myst.SkipParser(),
    ],
    patterns=["*.md"],
)

rest_examples = Sybil(
    parsers=[
        rest.DocTestParser(optionflags=ELLIPSIS),
        rest.PythonCodeBlockParser(),
    ],
    patterns=["*.py"],
)

pytest_collect_file = (markdown_examples + rest_examples).pytest()

collect_ignore = []
try:
    import sphinx  # noqa: F401
except ImportError:
    collect_ignore.extend(["docs"])

for name in ["fastapi", "pyramid", "flask", "aiohttp", "starlette"]:
    try:
        importlib.import_module(name)
    except ImportError:  # noqa: PERF203
        collect_ignore.extend([f"tests/integrations/test_{name}.py"])


@pytest.fixture(name="svc")
def _svc():
    return Service()


@pytest.fixture(name="rs")
def _rs(svc):
    return svcs.RegisteredService(Service, Service, False, True, None, True)


@pytest.fixture(name="registry")
def _registry():
    return svcs.Registry()


@pytest.fixture(name="container")
def _container(registry):
    return svcs.Container(registry)


@pytest.fixture(name="close_me")
def _close_me():
    return CloseMe()
