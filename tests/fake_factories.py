# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT


import asyncio


def nop(*_, **__):
    pass


def int_factory():
    return 42


def str_cleanup_factory():
    yield "foo"


async def async_int_factory():
    await asyncio.sleep(0)
    return 42


async def async_str_cleanup_factory():
    await asyncio.sleep(0)
    yield str(42)
    await asyncio.sleep(0)
