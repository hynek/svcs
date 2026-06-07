# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import contextlib
import inspect

from collections.abc import AsyncGenerator, Callable
from typing import Any, overload

import attrs

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

import svcs

from svcs._core import (
    _KEY_CONTAINER,
    _KEY_REGISTRY,
    T1,
    T2,
    T3,
    T4,
    T5,
    T6,
    T7,
    T8,
    T9,
    T10,
    TypeForm,
    _ServiceType,
)


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

    Args:
        lifespan: The lifespan function to make *svcs*-aware.
    """

    _lifespan: (
        Callable[
            [Starlette, svcs.Registry],
            contextlib.AbstractAsyncContextManager[dict[str, object]],
        ]
        | Callable[
            [Starlette, svcs.Registry],
            contextlib.AbstractAsyncContextManager[None],
        ]
        | Callable[
            [Starlette, svcs.Registry], AsyncGenerator[dict[str, object], None]
        ]
        | Callable[[Starlette, svcs.Registry], AsyncGenerator[None, None]]
    )
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
            cm = self._lifespan  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

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

    See Also:
        :ref:`aiohttp-health`
    """
    return svcs_from(request).get_pings()


async def aget_abstract(request: Request, *svc_types: _ServiceType) -> Any:
    """
    Same as :meth:`svcs.Container.aget_abstract()`, but uses container from
    *request*.

    .. deprecated:: 26.1.0
    """
    return await svcs_from(request).aget_abstract(*svc_types)


@overload
async def aget(request: Request, svc_type: TypeForm[T1], /) -> T1: ...


@overload
async def aget(
    request: Request,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    /,
) -> tuple[T1, T2]: ...


@overload
async def aget(
    request: Request,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    /,
) -> tuple[T1, T2, T3]: ...


@overload
async def aget(
    request: Request,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    /,
) -> tuple[T1, T2, T3, T4]: ...


@overload
async def aget(
    request: Request,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    /,
) -> tuple[T1, T2, T3, T4, T5]: ...


@overload
async def aget(
    request: Request,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6]: ...


@overload
async def aget(
    request: Request,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    svc_type7: TypeForm[T7],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7]: ...


@overload
async def aget(
    request: Request,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    svc_type7: TypeForm[T7],
    svc_type8: TypeForm[T8],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8]: ...


@overload
async def aget(
    request: Request,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    svc_type7: TypeForm[T7],
    svc_type8: TypeForm[T8],
    svc_type9: TypeForm[T9],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9]: ...


@overload
async def aget(
    request: Request,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    svc_type7: TypeForm[T7],
    svc_type8: TypeForm[T8],
    svc_type9: TypeForm[T9],
    svc_type10: TypeForm[T10],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9, T10]: ...


async def aget(request: Request, *svc_types: _ServiceType) -> object:
    """
    Same as :meth:`svcs.Container.aget`, but uses the container from *request*.
    """
    return await svcs_from(request).aget(*svc_types)
