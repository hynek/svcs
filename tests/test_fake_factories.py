# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Ensure our fake factories do what we want them to do.
"""

import sys

from collections.abc import AsyncGenerator, Generator

import pytest

from .fake_factories import (
    async_int_factory,
    async_str_gen_factory,
    int_factory,
    str_gen_factory,
)
from .helpers import nop


def test_nop():
    """
    nop takes any argument and returns always None.
    """
    assert None is nop()
    assert None is nop(1)
    assert None is nop(1, x=2)


def test_int_factory():
    """
    int_factory takes no arguments and returns an int.
    """
    assert isinstance(int_factory(), int)


def test_str_cleanup_factory():
    """
    str_cleanup_factory takes no arguments and returns a generator that yields
    a string.
    """
    gen = str_gen_factory()

    assert isinstance(gen, Generator)
    assert isinstance(next(gen), str)

    with pytest.raises(StopIteration):
        next(gen)


@pytest.mark.asyncio
async def test_async_int_factory():
    """
    async_int_factory takes no arguments and returns an int.
    """
    assert isinstance(await async_int_factory(), int)


@pytest.mark.asyncio
async def test_async_str_cleanup_factory():
    """
    async_str_cleanup_factory takes no arguments and returns an async generator
    that yields a string.
    """
    gen = async_str_gen_factory()

    assert isinstance(gen, AsyncGenerator)
    assert isinstance(await anext(gen), str)

    with pytest.raises(StopAsyncIteration):
        await anext(gen)


if sys.version_info < (3, 10):

    def anext(gen: AsyncGenerator):
        return gen.__anext__()
