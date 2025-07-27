# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from typing import Any, overload

from aiohttp import web

import svcs

from ._core import (
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
)


try:
    _AIOHTTP_KEY_REGISTRY = web.AppKey(_KEY_REGISTRY, svcs.Registry)
except (
    AttributeError
):  # pragma: no cover -- not adding a tox env for aiohttp<3.9
    _AIOHTTP_KEY_REGISTRY = _KEY_REGISTRY  # type: ignore[assignment]

# No equivalent of AppKey for Requests, yet?
_AIOHTTP_KEY_CONTAINER = _KEY_CONTAINER


def svcs_from(request: web.Request) -> svcs.Container:
    """
    Get the current container from *request*.
    """
    return request[_AIOHTTP_KEY_CONTAINER]  # type: ignore[no-any-return]


def get_registry(app: web.Application) -> svcs.Registry:
    """
    Get the registry from *app*.
    """
    return app[_AIOHTTP_KEY_REGISTRY]


def init_app(
    app: web.Application,
    *,
    registry: svcs.Registry | None = None,
    middleware_pos: int = 0,
) -> web.Application:
    """
    Initialize the application.

    Inserts the *svcs* middleware at *middleware_pos* which is 0 by default, so
    you can use :func:`svcs_from` and :func:`aget` in other middlewares.
    """
    app[_AIOHTTP_KEY_REGISTRY] = registry or svcs.Registry()
    app.middlewares.insert(middleware_pos, svcs_middleware)
    app.on_cleanup.append(aclose_registry)

    return app


@web.middleware
async def svcs_middleware(
    request: web.Request, handler: Callable
) -> web.Response:
    async with svcs.Container(request.app[_AIOHTTP_KEY_REGISTRY]) as container:
        request[_AIOHTTP_KEY_CONTAINER] = container

        return await handler(request)  # type: ignore[no-any-return]


def register_value(
    app: web.Application,
    svc_type: type,
    value: object,
    *,
    enter: bool = False,
    ping: Callable | None = None,
    on_registry_close: Callable | None = None,
) -> None:
    """
    Same as :meth:`svcs.Registry.register_value()`, but uses registry on
    *app*.
    """
    get_registry(app).register_value(
        svc_type,
        value,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
    )


def register_factory(
    app: web.Application,
    svc_type: type,
    factory: Callable,
    *,
    enter: bool = True,
    ping: Callable | None = None,
    on_registry_close: Callable | None = None,
) -> None:
    """
    Same as :meth:`svcs.Registry.register_factory()`, but uses registry on
    *app*.
    """
    get_registry(app).register_factory(
        svc_type,
        factory,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
    )


async def aclose_registry(app: web.Application) -> None:
    """
    Close the registry on *app*, if present.

    You probably don't have to call this yourself, because it's registered for
    the application as an {attr}`aiohttp.web.Application.on_cleanup` callback.

    See Also:
        :ref:`aiohttp-cleanup`
    """
    with suppress(KeyError):
        await get_registry(app).aclose()


def get_pings(request: web.Request) -> list[svcs.ServicePing]:
    """
    Same as :meth:`svcs.Container.get_pings`, but uses the container from
    *request*.

    See Also:
        :ref:`aiohttp-health`
    """
    return svcs_from(request).get_pings()


async def aget_abstract(request: web.Request, *svc_types: type) -> Any:
    """
    Same as :meth:`svcs.Container.aget_abstract()`, but uses container from
    *request*.
    """
    return await svcs_from(request).aget_abstract(*svc_types)


@overload
async def aget(request: web.Request, svc_type: type[T1], /) -> T1: ...


@overload
async def aget(
    request: web.Request, svc_type1: type[T1], svc_type2: type[T2], /
) -> tuple[T1, T2]: ...


@overload
async def aget(
    request: web.Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    /,
) -> tuple[T1, T2, T3]: ...


@overload
async def aget(
    request: web.Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    /,
) -> tuple[T1, T2, T3, T4]: ...


@overload
async def aget(
    request: web.Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    /,
) -> tuple[T1, T2, T3, T4, T5]: ...


@overload
async def aget(
    request: web.Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6]: ...


@overload
async def aget(
    request: web.Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    svc_type7: type[T7],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7]: ...


@overload
async def aget(
    request: web.Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    svc_type7: type[T7],
    svc_type8: type[T8],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8]: ...


@overload
async def aget(
    request: web.Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    svc_type7: type[T7],
    svc_type8: type[T8],
    svc_type9: type[T9],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9]: ...


@overload
async def aget(
    request: web.Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    svc_type7: type[T7],
    svc_type8: type[T8],
    svc_type9: type[T9],
    svc_type10: type[T10],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9, T10]: ...


async def aget(request: web.Request, *svc_types: type) -> object:
    """
    Same as :meth:`svcs.Container.aget`, but uses the container from *request*.
    """
    return await svcs_from(request).aget(*svc_types)
