# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from collections.abc import Generator
from typing import Protocol

from aiohttp.web import Application, Request

import svcs


def factory_with_cleanup() -> Generator[int, None, None]:
    yield 1


reg = svcs.Registry()

app = Application()
app = svcs.aiohttp.init_app(app, registry=reg)
app = svcs.aiohttp.init_app(app, registry=reg, middleware_pos=3)
app = svcs.aiohttp.init_app(app)

svcs.aiohttp.register_value(app, int, 1)
svcs.aiohttp.register_value(app, int, 1, ping=lambda: None)

svcs.aiohttp.register_factory(app, str, str)
svcs.aiohttp.register_factory(app, int, factory_with_cleanup)
svcs.aiohttp.register_value(app, str, str, ping=lambda: None)

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


class P(Protocol):
    def m(self) -> None: ...


async def func(request: Request) -> None:
    _a, _b, _c, _d, _e, _f, _g, _h, _i, _j = await svcs.aiohttp.aget(
        request, int, str, bool, tuple, object, float, list, dict, set, bytes
    )

    await svcs.aiohttp.aget_abstract(request, P)

    await svcs.aiohttp.aclose_registry(app)

    svcs.aiohttp.svcs_from(request)
