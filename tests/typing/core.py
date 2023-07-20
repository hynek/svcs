# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import contextlib
import sys

from typing import AsyncGenerator, Generator

import svc_reg


reg = svc_reg.Registry()


def gen() -> Generator:
    yield 42


async def async_gen() -> AsyncGenerator:
    yield 42


def factory_with_cleanup() -> Generator[int, None, None]:
    yield 1


reg.register_value(int, 1)
reg.register_value(int, 1, ping=lambda: None)
reg.register_value(int, gen)

reg.register_factory(str, str)
reg.register_factory(int, factory_with_cleanup)
reg.register_value(str, str, ping=lambda: None)
reg.register_value(str, async_gen)

con = svc_reg.Container(reg)

# The type checker believes whatever we tell it.
o1: object = con.get(object)
o2: int = con.get(object)

con.close()

with contextlib.closing(svc_reg.Container(reg)) as con:
    ...

if sys.version_info >= (3, 10):

    async def f() -> None:
        async with contextlib.aclosing(svc_reg.Container(reg)):
            ...
