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
    _instantiated: dict[type, object] = attrs.Factory(dict)
    _cleanups: list[
        tuple[RegisteredService, Generator | AsyncGenerator]
    ] = attrs.Factory(list)

    def __repr__(self) -> str:
        return (
            f"<Container(instantiated={len(self._instantiated)}, "
            f"cleanups={len(self._cleanups)})>"
        )

    def get(self, svc_type: type) -> Any:
        """
        Get an instance of *svc_type*.

        Instantiate it if necessary and register its cleanup.

        Returns:
             Any until https://github.com/python/mypy/issues/4717 is fixed.
        """
        if (svc := self._instantiated.get(svc_type)) is not None:
            return svc

        rs = self.registry.get_registered_service_for(svc_type)
        svc = rs.factory()

        if isinstance(svc, Generator):
            self._cleanups.append((rs, svc))
            svc = next(svc)

        self._instantiated[rs.svc_type] = svc

        return svc

    async def aget(self, svc_type: type) -> Any:
        """
        Get an instance of *svc_type*.

        Instantiate it asynchronously if necessary and register its cleanup.

        Returns:
             Any until https://github.com/python/mypy/issues/4717 is fixed.
        """
        if (svc := self._instantiated.get(svc_type)) is not None:
            return svc

        rs = self.registry.get_registered_service_for(svc_type)
        svc = rs.factory()

        if isinstance(svc, AsyncGenerator):
            self._cleanups.append((rs, svc))
            svc = await anext(svc)
        elif isawaitable(svc):
            svc = await svc

        self._instantiated[rs.svc_type] = svc

        return svc

    def forget_service_type(self, svc_type: type) -> None:
        """
        Remove all traces of *svc_type* in ourselves.
        """
        with suppress(KeyError):
            del self._instantiated[svc_type]

    def close(self) -> None:
        """
        Run all registered *synchronous* cleanups.

        Async closes are *not* awaited.
        """
        for rs, gen in reversed(self._cleanups):
            try:
                if isinstance(gen, AsyncGenerator):
                    warnings.warn(
                        f"Skipped async cleanup for {rs.name!r}. "
                        "Use aclose() instead.",
                        # stacklevel doesn't matter here; it's coming from a framework.
                        stacklevel=1,
                    )
                    continue

                next(gen)

                warnings.warn(
                    f"Container clean up for {rs.name!r} didn't stop iterating.",
                    stacklevel=1,
                )
            except StopIteration:  # noqa: PERF203
                pass
            except Exception:  # noqa: BLE001
                log.warning(
                    "Container clean up failed for %r.",
                    rs.name,
                    exc_info=True,
                    extra={"svcs_service_name": rs.name},
                )

        self._cleanups.clear()
        self._instantiated.clear()

    async def aclose(self) -> None:
        """
        Run *all* registered cleanups -- synchronous **and** asynchronous.
        """
        for rs, gen in reversed(self._cleanups):
            try:
                if isinstance(gen, AsyncGenerator):
                    await anext(gen)
                else:
                    next(gen)

                warnings.warn(
                    f"Container clean up for {rs.name!r} didn't stop iterating.",
                    stacklevel=1,
                )

            except (StopAsyncIteration, StopIteration):  # noqa: PERF203
                pass
            except Exception:  # noqa: BLE001
                log.warning(
                    "Container clean up failed for %r.",
                    rs.name,
                    exc_info=True,
                    extra={"svcs_service_name": rs.name},
                )

        self._cleanups.clear()
        self._instantiated.clear()

    def get_pings(self) -> list[ServicePing]:
        """
        Get all pingable services and bind them to ourselves for cleanups.
        """
        return [
            ServicePing(self, rs)
            for rs in self.registry._services.values()
            if rs.ping is not None
        ]


@attrs.frozen
class RegisteredService:
    svc_type: type
    factory: Callable = attrs.field(hash=False)
    ping: Callable | None = attrs.field(hash=False)

    @property
    def name(self) -> str:
        return f"{ self.svc_type.__module__ }.{self.svc_type.__qualname__}"

    def __repr__(self) -> str:
        return (
            f"<RegisteredService(svc_type="
            f"{ self.name}, "
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
    _services: dict[type, RegisteredService] = attrs.Factory(dict)
    _on_close: list[tuple[str, Callable]] = attrs.Factory(list)

    def register_factory(
        self,
        svc_type: type,
        factory: Callable,
        *,
        ping: Callable | None = None,
        on_registry_close: Callable | None = None,
    ) -> None:
        rs = RegisteredService(svc_type, factory, ping)
        self._services[svc_type] = rs

        if on_registry_close is not None:
            self._on_close.append((rs.name, on_registry_close))

    def register_value(
        self,
        svc_type: type,
        instance: object,
        *,
        ping: Callable | None = None,
        on_registry_close: Callable | None = None,
    ) -> None:
        self.register_factory(
            svc_type,
            lambda: instance,
            ping=ping,
            on_registry_close=on_registry_close,
        )

    def get_registered_service_for(self, svc_type: type) -> RegisteredService:
        try:
            return self._services[svc_type]
        except KeyError:
            raise ServiceNotFoundError(svc_type) from None

    def close(self) -> None:
        """
        Clear registrations & run synchronous ``on_registry_close`` callbacks.
        """
        for name, oc in reversed(self._on_close):
            if iscoroutinefunction(oc):
                warnings.warn(
                    f"Skipped async cleanup for {name!r}. "
                    "Use aclose() instead.",
                    # stacklevel doesn't matter here; it's coming from a
                    # framework.
                    stacklevel=1,
                )
                continue

            try:
                log.debug("closing %r", name)
                oc()
                log.debug("closed %r", name)
            except Exception:  # noqa: BLE001, PERF203
                log.warning(
                    "Registry's on_registry_close hook failed for %r.",
                    name,
                    exc_info=True,
                    extra={"svcs_service_name": name},
                )

        self._services.clear()
        self._on_close.clear()

    async def aclose(self) -> None:
        """
        Clear registrations & run all ``on_registry_close`` callbacks.
        """
        for name, oc in reversed(self._on_close):
            try:
                if iscoroutinefunction(oc) or isawaitable(oc):
                    log.debug("async closing %r", name)
                    await oc()
                    log.debug("async closed %r", name)
                else:
                    log.debug("closing %r", name)
                    oc()
                    log.debug("closed %r", name)
            except Exception:  # noqa: BLE001, PERF203
                log.warning(
                    "Registry's on_registry_close hook failed for %r.",
                    name,
                    exc_info=True,
                    extra={"svcs_service_name": name},
                )

        self._services.clear()
        self._on_close.clear()
