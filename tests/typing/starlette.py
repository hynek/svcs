# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from typing import Protocol

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request

import svcs


def factory_with_cleanup() -> Generator[int, None, None]:
    yield 1


@svcs.starlette.lifespan
async def lifespan(
    app: Starlette, registry: svcs.Registry
) -> AsyncGenerator[dict[str, object], None]:
    yield {}


reg: svcs.Registry = lifespan.registry


@svcs.starlette.lifespan
async def lifespan2(
    app: Starlette, registry: svcs.Registry
) -> AsyncGenerator[None, None]:
    yield


@svcs.starlette.lifespan
@asynccontextmanager
async def lifespan3(
    app: Starlette, registry: svcs.Registry
) -> AsyncGenerator[dict[str, object], None]:
    yield {}


@svcs.starlette.lifespan
@asynccontextmanager
async def lifespan4(
    app: Starlette, registry: svcs.Registry
) -> AsyncGenerator[None, None]:
    yield


reg = svcs.Registry()

app = Starlette(
    lifespan=lifespan, middleware=[Middleware(svcs.starlette.SVCSMiddleware)]
)

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

request = Request({})


class P(Protocol):
    def m(self) -> None: ...


async def func() -> None:
    a, b, c, d, e, f, g, h, i, j = await svcs.starlette.aget(
        request, int, str, bool, tuple, object, float, list, dict, set, bytes
    )

    p: P = await svcs.starlette.aget_abstract(request, P)


con: svcs.Container = svcs.starlette.svcs_from(request)
