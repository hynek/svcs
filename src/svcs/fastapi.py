# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import contextlib
import inspect

from collections.abc import AsyncGenerator
from typing import Annotated, Callable

import attrs

from fastapi import Depends, FastAPI, Request

import svcs

from svcs._core import _KEY_REGISTRY


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

    _lifespan: (
        Callable[
            [FastAPI, svcs.Registry],
            contextlib.AbstractAsyncContextManager[dict[str, object]],
        ]
        | Callable[
            [FastAPI, svcs.Registry],
            contextlib.AbstractAsyncContextManager[None],
        ]
        | Callable[
            [FastAPI, svcs.Registry], AsyncGenerator[dict[str, object], None]
        ]
        | Callable[[FastAPI, svcs.Registry], AsyncGenerator[None, None]]
    )
    _state: dict[str, object] = attrs.field(factory=dict)
    registry: svcs.Registry = attrs.field(factory=svcs.Registry)

    @contextlib.asynccontextmanager
    async def __call__(
        self, app: FastAPI
    ) -> AsyncGenerator[dict[str, object], None]:
        cm: Callable[
            [FastAPI, svcs.Registry], contextlib.AbstractAsyncContextManager
        ]
        if inspect.isasyncgenfunction(self._lifespan):
            cm = contextlib.asynccontextmanager(self._lifespan)
        else:
            cm = self._lifespan  # type: ignore[assignment]

        async with self.registry, cm(app, self.registry) as state:
            self._state = state or {}
            self._state[_KEY_REGISTRY] = self.registry
            yield self._state


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
