# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
import sys
import warnings

from collections.abc import Callable
from contextlib import suppress
from inspect import isasyncgenfunction, isawaitable, iscoroutinefunction
from typing import Any, AsyncGenerator, Generator

import attrs

from .exceptions import ServiceNotFoundError


log = logging.getLogger(__name__)

if sys.version_info < (3, 10):

    def anext(gen: AsyncGenerator) -> Any:
        return gen.__anext__()


@attrs.define
class Container:
    """
    A per-context container for instantiated services & cleanups.
    """

    registry: Registry
    instantiated: dict[type, object] = attrs.Factory(dict)
    cleanups: list[
        tuple[RegisteredService, Generator | AsyncGenerator]
    ] = attrs.Factory(list)

    def __repr__(self) -> str:
        return (
            f"<Container(instantiated={len(self.instantiated)}, "
            f"cleanups={len(self.cleanups)})>"
        )

    def get(self, svc_type: type) -> Any:
        """
        Get an instance of *svc_type*.

        Instantiate it if necessary and register its cleanup.

        Returns:
             Any until https://github.com/python/mypy/issues/4717 is fixed.
        """
        if (svc := self.instantiated.get(svc_type)) is not None:
            return svc

        rs = self.registry.get_registered_service_for(svc_type)
        svc = rs.factory()

        if isinstance(svc, Generator):
            self.cleanups.append((rs, svc))
            svc = next(svc)

        self.instantiated[rs.svc_type] = svc

        return svc

    async def aget(self, svc_type: type) -> Any:
        """
        Get an instance of *svc_type*.

        Instantiate it asynchronously if necessary and register its cleanup.

        Returns:
             Any until https://github.com/python/mypy/issues/4717 is fixed.
        """
        if (svc := self.instantiated.get(svc_type)) is not None:
            return svc

        rs = self.registry.get_registered_service_for(svc_type)
        svc = rs.factory()

        if isinstance(svc, AsyncGenerator):
            self.cleanups.append((rs, svc))
            svc = await anext(svc)
        elif isawaitable(svc):
            svc = await svc

        self.instantiated[rs.svc_type] = svc

        return svc

    def forget_service_type(self, svc_type: type) -> None:
        """
        Remove all traces of *svc_type*.
        """
        with suppress(KeyError):
            del self.instantiated[svc_type]

    def close(self) -> None:
        """
        Run all synchronous registered cleanups.

        Async closes are *not* awaited.
        """
        while self.cleanups:
            rs, gen = self.cleanups.pop()
            try:
                if isinstance(gen, AsyncGenerator):
                    warnings.warn(
                        f"Skipped async cleanup for {rs!r}. "
                        "Use aclose() instead.",
                        # stacklevel doesn't matter here; it's coming from a framework.
                        stacklevel=1,
                    )
                    continue

                next(gen)

                warnings.warn(
                    f"clean up for {rs!r} didn't stop iterating", stacklevel=1
                )
            except StopIteration:  # noqa: PERF203
                pass
            except Exception:  # noqa: BLE001
                log.warning(
                    "clean up failed",
                    exc_info=True,
                    extra={"service": rs.name},
                )

    async def aclose(self) -> None:
        """
        Run *all* registered cleanups -- synchronous **and** asynchronous.
        """
        while self.cleanups:
            rs, gen = self.cleanups.pop()
            try:
                if isinstance(gen, AsyncGenerator):
                    await anext(gen)
                else:
                    next(gen)

                warnings.warn(
                    f"clean up for {rs!r} didn't stop iterating", stacklevel=1
                )

            except (StopAsyncIteration, StopIteration):  # noqa: PERF203
                pass
            except Exception:  # noqa: BLE001
                log.warning(
                    "clean up failed",
                    exc_info=True,
                    extra={"service": rs.name},
                )

    def get_pings(self) -> list[ServicePing]:
        """
        Get all pingable services and bind them to ourselves for cleanups.
        """
        return [
            ServicePing(self, rs)
            for rs in self.registry.services.values()
            if rs.ping is not None
        ]


@attrs.frozen
class RegisteredService:
    svc_type: type
    factory: Callable = attrs.field(hash=False)
    ping: Callable | None = attrs.field(hash=False)

    @property
    def name(self) -> str:
        return self.svc_type.__qualname__

    def __repr__(self) -> str:
        return (
            f"<RegisteredService(svc_type={ self.svc_type.__module__ }."
            f"{ self.svc_type.__qualname__ }, "
            f"has_ping={ self.ping is not None})>"
        )

    @property
    def is_async(self) -> bool:
        return iscoroutinefunction(self.factory) or isasyncgenfunction(
            self.factory
        )


@attrs.frozen
class ServicePing:
    _container: Container
    _rs: RegisteredService

    def ping(self) -> None:
        svc = self._container.get(self._rs.svc_type)
        self._rs.ping(svc)  # type: ignore[misc]

    async def aping(self) -> None:
        svc = await self._container.aget(self._rs.svc_type)
        if iscoroutinefunction(self._rs.ping):
            await self._rs.ping(svc)
        else:
            self._rs.ping(svc)  # type: ignore[misc]

    @property
    def name(self) -> str:
        return self._rs.name

    @property
    def is_async(self) -> bool:
        """
        Return True if you have to use `aping` instead of `ping`.
        """
        return self._rs.is_async or iscoroutinefunction(self._rs.ping)


@attrs.define
class Registry:
    services: dict[type, RegisteredService] = attrs.Factory(dict)

    def register_factory(
        self,
        svc_type: type,
        factory: Callable,
        *,
        ping: Callable | None = None,
    ) -> None:
        self.services[svc_type] = RegisteredService(svc_type, factory, ping)

    def register_value(
        self,
        svc_type: type,
        instance: object,
        *,
        ping: Callable | None = None,
    ) -> None:
        self.register_factory(svc_type, lambda: instance, ping=ping)

    def get_registered_service_for(self, svc_type: type) -> RegisteredService:
        try:
            return self.services[svc_type]
        except KeyError:
            raise ServiceNotFoundError(svc_type) from None
