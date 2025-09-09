# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import contextlib
import sys

from collections.abc import AsyncGenerator, Generator
from typing import NewType, Protocol

import svcs


reg = svcs.Registry()
con = svcs.Container(reg)

reg.close()
with contextlib.closing(reg) as reg:
    ...
with reg as reg:
    reg.register_factory(int, int)


async def func() -> None:
    await reg.aclose()
    await con.aclose()

    async with svcs.Registry() as reg2:
        reg2.register_factory(int, int)

        async with svcs.Container(reg2) as con2:
            a: int
            b: str
            c: bool
            d: tuple
            e: object
            f: float
            g: list
            h: dict
            i: set
            j: bytes
            a, b, c, d, e, f, g, h, i, j = await con2.aget(
                int, str, bool, tuple, object, float, list, dict, set, bytes
            )


def gen() -> Generator:
    yield 42


async def async_gen() -> AsyncGenerator:
    yield 42


@contextlib.asynccontextmanager
async def async_cm() -> AsyncGenerator:
    yield 42


def factory_with_cleanup() -> Generator[int, None, None]:
    yield 1


@contextlib.contextmanager
def factory_with_cleanup_ctx() -> Generator[int, None, None]:
    yield 1


def factory_that_takes_container_by_annotation(foo: svcs.Container) -> int:
    return 1


async def async_ping() -> None:
    pass


reg.register_value(int, 1)
reg.register_value(int, 1, ping=lambda: None)
reg.register_value(int, 1, ping=async_ping)
reg.register_value(int, gen)

reg.register_factory(str, str)
reg.register_factory(int, factory_with_cleanup)
reg.register_factory(int, factory_with_cleanup_ctx)
reg.register_factory(int, factory_with_cleanup, ping=async_ping)
reg.register_factory(str, async_gen)
reg.register_factory(str, async_cm)
reg.register_value(str, str, ping=lambda: None)

con = svcs.Container(reg)

# Local registries
con.register_local_factory(int, factory_with_cleanup)
con.register_local_value(int, 42)

# The type checker believes whatever we tell it.
o1: object = con.get(object)
o2: int = con.get(int)

a: int
b: str
c: bool
d: tuple
e: object
f: float
g: list
h: dict
i: set
j: bytes
a, b, c, d, e, f, g, h, i, j = con.get(
    int, str, bool, tuple, object, float, list, dict, set, bytes
)


class P(Protocol):
    def m(self) -> None: ...


p: P = con.get_abstract(P)

con.close()

with contextlib.closing(svcs.Container(reg)) as con:
    ...

with svcs.Container(reg) as con:
    i2: int = con.get(int)

if sys.version_info >= (3, 10):

    async def ctx() -> None:
        async with contextlib.aclosing(svcs.Container(reg)):
            ...

        async with contextlib.aclosing(svcs.Registry()):
            ...


# Multiple factories for same type:
S1 = NewType("S1", str)
S2 = NewType("S2", str)

reg.register_value(S1, "foo")
reg.register_value(S2, "bar")

s1: str = con.get(S1)
s2: str = con.get(S2)
