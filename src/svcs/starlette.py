# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import contextlib
import inspect
import sys

from typing import Any, AsyncGenerator, Callable, overload

import attrs

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

import svcs

from svcs._core import _KEY_CONTAINER, _KEY_REGISTRY, T, Ts


if sys.version_info < (3, 11):
    from typing_extensions import Unpack
else:
    from typing import Unpack


def svcs_from(request: Request) -> svcs.Container:
    """
    Get the current container from *request*.
    """
    return getattr(request.state, _KEY_CONTAINER)  # type: ignore[no-any-return]


@attrs.define
class lifespan:  # noqa: N801
    """
    Make a Starlette lifespan *svcs*-aware.

    Makes sure that the registry is available to the decorated lifespan
    function as a second parameter and that the registry is closed when the
    application exists.

    Async generators are automatically wrapped into an async context manager.

    Arguments:
        lifespan: The lifespan function to make *svcs*-aware.
    """

    _lifespan: Callable[
        [Starlette, svcs.Registry],
        contextlib.AbstractAsyncContextManager[dict[str, object]],
    ] | Callable[
        [Starlette, svcs.Registry],
        contextlib.AbstractAsyncContextManager[None],
    ] | Callable[
        [Starlette, svcs.Registry], AsyncGenerator[dict[str, object], None]
    ] | Callable[
        [Starlette, svcs.Registry], AsyncGenerator[None, None]
    ]
    _state: dict[str, object] = attrs.field(factory=dict)
    registry: svcs.Registry = attrs.field(factory=svcs.Registry)

    @contextlib.asynccontextmanager
    async def __call__(
        self, app: Starlette
    ) -> AsyncGenerator[dict[str, object], None]:
        cm: Callable[
            [Starlette, svcs.Registry], contextlib.AbstractAsyncContextManager
        ]
        if inspect.isasyncgenfunction(self._lifespan):
            cm = contextlib.asynccontextmanager(self._lifespan)
        else:
            cm = self._lifespan  # type: ignore[assignment]

        async with self.registry, cm(app, self.registry) as state:
            self._state = state or {}
            self._state[_KEY_REGISTRY] = self.registry
            yield self._state


@attrs.define
class SVCSMiddleware:
    """
    Attach a :class:`svcs.Container` to the request state, based on a registry
    that has been put on the request state by :class:`lifespan`. Closes the
    container at the end of a request or websocket connection.
    """

    app: ASGIApp

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)

        async with svcs.Container(scope["state"][_KEY_REGISTRY]) as con:
            scope["state"][_KEY_CONTAINER] = con

            return await self.app(scope, receive, send)


def get_pings(request: Request) -> list[svcs.ServicePing]:
    """
    Same as :meth:`svcs.Container.get_pings`, but uses the container from
    *request*.

    .. seealso:: :ref:`aiohttp-health`
    """
    return svcs_from(request).get_pings()


async def aget_abstract(request: Request, *svc_types: type) -> Any:
    """
    Same as :meth:`svcs.Container.aget_abstract()`, but uses container from
    *request*.
    """
    return await svcs_from(request).aget_abstract(*svc_types)


@overload
async def aget(request: Request, svc_type: type[T], /) -> T:
    ...


@overload
async def aget(request: Request, *svc_types: Unpack[Ts]) -> tuple[Unpack[Ts]]:
    ...


async def aget(request: Request, *svc_types: type) -> object:
    """
    Same as :meth:`svcs.Container.aget`, but uses the container from *request*.
    """
    return await svcs_from(request).aget(*svc_types)
