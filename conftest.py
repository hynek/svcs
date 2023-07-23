# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from doctest import ELLIPSIS

import pytest

from sybil import Sybil
from sybil.parsers import myst, rest

import svc_reg


markdown_examples = Sybil(
    parsers=[
        myst.DocTestDirectiveParser(optionflags=ELLIPSIS),
        myst.PythonCodeBlockParser(),
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


@pytest.fixture(name="registry")
def _registry():
    return svc_reg.Registry()


@pytest.fixture(name="container")
def _container(registry):
    return svc_reg.Container(registry)
