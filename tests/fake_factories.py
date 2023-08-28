# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio

from contextlib import asynccontextmanager, contextmanager


def int_factory():
    return 42


def str_gen_factory():
    yield "foo"


@contextmanager
def bool_cm_factory():
    yield True


async def async_int_factory():
    await asyncio.sleep(0)
    return 42


async def async_str_gen_factory():
    await asyncio.sleep(0)
    yield str(42)
    await asyncio.sleep(0)


@asynccontextmanager
async def async_bool_cm_factory():
    await asyncio.sleep(0)
    yield True
