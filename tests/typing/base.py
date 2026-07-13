# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import contextlib
import sys

from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from typing import Annotated, NewType, Protocol

import svcs


if sys.version_info < (3, 11):
    from typing_extensions import assert_type
else:
    from typing import assert_type


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
assert_type(con.get(object), object)
assert_type(con.get(int), int)
assert_type(
    con.get(int, str, bool, tuple, object, float, list, dict, set, bytes),
    tuple[int, str, bool, tuple, object, float, list, dict, set, bytes],
)


class P(Protocol):
    def m(self) -> None: ...


assert_type(con.get(P), P)

# Just make sure it passes even tho it's Any.
p: P = con.get_abstract(P)

con.close()

with contextlib.closing(svcs.Container(reg)) as con:
    ...

with svcs.Container(reg) as con:
    assert_type(con.get(int), int)


async def ctx() -> None:
    async with contextlib.aclosing(svcs.Container(reg)):
        ...

    async with contextlib.aclosing(svcs.Registry()):
        ...


# Multiple factories for same type:
class S1(str):
    pass


S2 = NewType("S2", str)
S3 = Annotated[str, "S3"]


reg.register_value(S1, "foo")
reg.register_value(S2, "bar")  # pyright:ignore[reportArgumentType]
reg.register_value(S3, "qux")  # pyright:ignore[reportArgumentType]

assert_type(con.get(S1), S1)
assert_type(con.get(S2), S2)  # pyright:ignore[reportAssertTypeFailure,reportArgumentType]
assert_type(con.get(S3), S3)  # pyright:ignore[reportAssertTypeFailure,reportArgumentType]

s: str = con.get(S1)
s = con.get(S2)  # pyright:ignore[reportArgumentType]
s = con.get(S3)  # pyright:ignore[reportArgumentType]


# Register instances of custom classes as values
class Foo:
    pass


foo = Foo()

reg.register_value(Foo, foo)


# Autowire
@svcs.autowire
def fn(a: str, /, b: int, *, c: bool) -> str:
    return "fn"


@svcs.aautowire
async def afn(a: str, /, b: int, *, c: bool) -> str:
    return "afn"


assert_type(fn, Callable[[svcs.Container], str])
assert_type(afn, Callable[[svcs.Container], Awaitable[str]])
assert_type(svcs.autowire(P), Callable[[svcs.Container], P])
assert_type(svcs.aautowire(P), Callable[[svcs.Container], Awaitable[P]])

reg.register_factory(str, fn)
reg.register_factory(str, afn)
reg.register_factory(P, svcs.autowire(P))
reg.register_factory(P, svcs.aautowire(P))
