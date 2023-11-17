# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import sys
import typing

import pytest

import svcs


@pytest.mark.skipif(sys.version_info < (3, 10), reason="requires Python 3.10+")
def test_get_type_hints():
    """
    typing.get_type_hints() works on our objects on Python 3.10+.

    Unfortunately supporting older versions would require to rewrite all type
    hints.

    Regression test for #52.
    """
    typing.get_type_hints(svcs.Registry)
    typing.get_type_hints(svcs.Container)
    typing.get_type_hints(svcs.ServicePing)
    typing.get_type_hints(svcs.RegisteredService)
