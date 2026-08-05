# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import contextlib
import inspect

from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING, Annotated, Any, TypeAlias, cast

import attrs

from fastapi import Depends, FastAPI, Request

import svcs

from svcs._core import _KEY_REGISTRY


if TYPE_CHECKING:
    from fastapi.testclient import TestClient
else:
    try:
        from fastapi.testclient import TestClient
    except (ImportError, RuntimeError):  # pragma: no cover
        TestClient = Any


AsyncGenLifespan: TypeAlias = Callable[
    [FastAPI, svcs.Registry],
    AsyncGenerator[dict[str, object] | None, None],
]
AsyncCMLifespan: TypeAlias = Callable[
    [FastAPI, svcs.Registry],
    contextlib.AbstractAsyncContextManager[dict[str, object] | None],
]
SomeLifespan: TypeAlias = AsyncGenLifespan | AsyncCMLifespan


@attrs.define
class lifespan:  # noqa: N801
    """
    Make a FastAPI lifespan *svcs*-aware.

    Makes sure that the registry is available to the decorated lifespan
    function as a second parameter and that the registry is closed when the
    application exists.

    Async generators are automatically wrapped into an async context manager.

    Args:
        lifespan: The lifespan function to make *svcs*-aware.
    """

    _lifespan: SomeLifespan
    _state: dict[str, object] = attrs.field(factory=dict)
    registry: svcs.Registry = attrs.field(factory=svcs.Registry)

    @contextlib.asynccontextmanager
    async def __call__(
        self, app: FastAPI
    ) -> AsyncGenerator[dict[str, object], None]:
        cm: AsyncCMLifespan
        if inspect.isasyncgenfunction(self._lifespan):
            cm = contextlib.asynccontextmanager(
                cast(AsyncGenLifespan, self._lifespan)
            )
        else:
            cm = cast(AsyncCMLifespan, self._lifespan)

        # FastAPI enters merged lifespans app-first, but merges their
        # states first-wins.  Mirror that precedence: only the first
        # svcs lifespan attaches its registry and detaches it on exit.
        owns_app_state = not hasattr(app.state, _KEY_REGISTRY)
        if owns_app_state:
            setattr(app.state, _KEY_REGISTRY, self.registry)
        try:
            async with self.registry, cm(app, self.registry) as state:
                self._state = state or {}
                self._state[_KEY_REGISTRY] = self.registry
                yield self._state
        finally:
            if owns_app_state:
                delattr(app.state, _KEY_REGISTRY)


def get_registry(app: FastAPI | TestClient) -> svcs.Registry:
    """
    Get the registry that :class:`lifespan` has attached to *app*.

    The registry is attached when the application starts, so this only works
    on a running application.

    Args:
        app:
            A FastAPI application with a *svcs*-aware lifespan, or a
            :class:`fastapi.testclient.TestClient` wrapping one.

    Raises:
        LookupError: If no registry is attached to *app*.

    .. versionadded:: 26.2.0
    """
    try:
        if not isinstance(app, FastAPI):
            app = cast("FastAPI", app.app)
        return getattr(app.state, _KEY_REGISTRY)  # type: ignore[no-any-return]
    except AttributeError:
        msg = "No svcs registry on app."
        raise LookupError(msg) from None


async def container(request: Request) -> AsyncGenerator[svcs.Container, None]:
    """
    A FastAPI `dependency
    <https://fastapi.tiangolo.com/tutorial/dependencies/>`_ that provides you
    with a request-scoped container.

    Yields:
        A :class:`svcs.Container` that is cleaned up after the request.
    """
    async with svcs.Container(getattr(request.state, _KEY_REGISTRY)) as cont:
        yield cont


DepContainer = Annotated[svcs.Container, Depends(container)]
"""
An alias for::

    typing.Annotated[svcs.Container, fastapi.Depends(svcs.fastapi.container)]

This allows you write your view like::

    @app.get("/")
    async def view(services: svcs.fastapi.DepContainer):
        ...
"""


async def registry(request: Request) -> svcs.Registry:
    """
    A FastAPI `dependency
    <https://fastapi.tiangolo.com/tutorial/dependencies/>`_ that provides you
    with the application's registry.

    .. versionadded:: 26.2.0
    """
    return getattr(request.state, _KEY_REGISTRY)  # type: ignore[no-any-return]


DepRegistry = Annotated[svcs.Registry, Depends(registry)]
"""
An alias for::

    typing.Annotated[svcs.Registry, fastapi.Depends(svcs.fastapi.registry)]

This allows you write your view like::

    @app.get("/")
    async def view(registry: svcs.fastapi.DepRegistry):
        ...

.. versionadded:: 26.2.0
"""
