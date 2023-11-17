# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import typing

import svcs


def test_get_type_hints():
    """
    typing.get_type_hints() works on our objects.

    Regression test for #52.
    """
    typing.get_type_hints(svcs.Registry)
    typing.get_type_hints(svcs.Container)
