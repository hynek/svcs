# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import inspect
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
    _on_close: list[tuple[str, Generator | AsyncGenerator]] = attrs.Factory(
        list
    )

    def __repr__(self) -> str:
        return (
            f"<Container(instantiated={len(self._instantiated)}, "
            f"cleanups={len(self._on_close)})>"
        )

    def get(self, svc_type: type) -> Any:
        """
        Get an instance of *svc_type*.

        Instantiate it if necessary and register its cleanup.

        Returns:
             :class:`typing.Any` until
             https://github.com/python/mypy/issues/4717 is fixed.
        """
        if (svc := self._instantiated.get(svc_type)) is not None:
            return svc

        rs = self.registry.get_registered_service_for(svc_type)
        svc = rs.factory(self) if rs.takes_container else rs.factory()

        if isinstance(svc, Generator):
            self._on_close.append((rs.name, svc))
            svc = next(svc)

        self._instantiated[svc_type] = svc

        return svc

    async def aget(self, svc_type: type) -> Any:
        """
        Get an instance of *svc_type*.

        Instantiate it asynchronously if necessary and register its cleanup.

        Returns:
             :class:`typing.Any` until
             https://github.com/python/mypy/issues/4717 is fixed.
        """
        if (svc := self._instantiated.get(svc_type)) is not None:
            return svc

        rs = self.registry.get_registered_service_for(svc_type)
        svc = rs.factory()

        if isinstance(svc, AsyncGenerator):
            self._on_close.append((rs.name, svc))
            svc = await anext(svc)
        elif isawaitable(svc):
            svc = await svc

        self._instantiated[rs.svc_type] = svc

        return svc

    def forget_about(self, svc_type: type) -> None:
        """
        Remove all traces of *svc_type* from ourselves.
        """
        with suppress(KeyError):
            del self._instantiated[svc_type]

    def close(self) -> None:
        """
        Run all registered *synchronous* cleanups.

        Async closes are *not* awaited.
        """
        for name, gen in reversed(self._on_close):
            try:
                if isinstance(gen, AsyncGenerator):
                    warnings.warn(
                        f"Skipped async cleanup for {name!r}. "
                        "Use aclose() instead.",
                        # stacklevel doesn't matter here; it's coming from a framework.
                        stacklevel=1,
                    )
                    continue

                next(gen)

                warnings.warn(
                    f"Container clean up for {name!r} didn't stop iterating.",
                    stacklevel=1,
                )
            except StopIteration:  # noqa: PERF203
                pass
            except Exception:  # noqa: BLE001
                log.warning(
                    "Container clean up failed for %r.",
                    name,
                    exc_info=True,
                    extra={"svcs_service_name": name},
                )

        self._on_close.clear()
        self._instantiated.clear()

    async def aclose(self) -> None:
        """
        Run *all* registered cleanups -- synchronous **and** asynchronous.
        """
        for name, gen in reversed(self._on_close):
            try:
                if isinstance(gen, AsyncGenerator):
                    await anext(gen)
                else:
                    next(gen)

                warnings.warn(
                    f"Container clean up for {name!r} didn't stop iterating.",
                    stacklevel=1,
                )

            except (StopAsyncIteration, StopIteration):  # noqa: PERF203
                pass
            except Exception:  # noqa: BLE001
                log.warning(
                    "Container clean up failed for %r.",
                    name,
                    exc_info=True,
                    extra={"svcs_service_name": name},
                )

        self._on_close.clear()
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
    takes_container: bool
    is_async: bool
    ping: Callable | None = attrs.field(hash=False)

    @property
    def name(self) -> str:
        return f"{ self.svc_type.__module__ }.{self.svc_type.__qualname__}"

    def __repr__(self) -> str:
        return (
            f"<RegisteredService(svc_type="
            f"{self.name}, "
            f"{self.factory}, "
            f"takes_container={self.takes_container}, "
            f"has_ping={ self.ping is not None}"
            ")>"
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

    def __repr__(self) -> str:
        return f"<svcs.Registry(num_services={len(self._services)})>"

    def register_factory(
        self,
        svc_type: type,
        factory: Callable,
        *,
        ping: Callable | None = None,
        on_registry_close: Callable | None = None,
    ) -> None:
        """
        Register *factory* for *svc_type*.

        Args:
            svc_type: The type of the service to register.

            factory: A callable that is used to instantiated *svc_type* if
                asked. If it's a generator, a cleanup is registered after
                instantiation. Can be also async or an async generator.

            ping: A callable that marks the service as having a health check.
                The service iss returned when :meth:`Container.get_pings` is
                called and *ping* is called as part of :meth:`ServicePing.ping`
                or :meth:`ServicePing.aping`.

            on_registry_close: A callable that is called when the
                :meth:`Registry.close()` method is called. Can be async, then
                :meth:`Registry.aclose()` must be called.
        """
        rs = RegisteredService(
            svc_type,
            factory,
            _takes_container(factory),
            iscoroutinefunction(factory) or isasyncgenfunction(factory),
            ping,
        )
        self._services[svc_type] = rs

        if on_registry_close is not None:
            self._on_close.append((rs.name, on_registry_close))

    def register_value(
        self,
        svc_type: type,
        value: object,
        *,
        ping: Callable | None = None,
        on_registry_close: Callable | None = None,
    ) -> None:
        """
        Syntactic sugar for ``register_factory(svc_type, lambda: value,
        ping=ping, on_registry_close=on_registry_close)``.
        """
        self.register_factory(
            svc_type,
            lambda: value,
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
            except Exception:  # noqa: BLE001
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


def _takes_container(factory: Callable) -> bool:
    """
    Return True if *factory* takes a svcs.Container as its first argument.
    """
    sig = inspect.signature(factory)
    if not sig.parameters:
        return False

    if len(sig.parameters) != 1:
        msg = "Factories must take 0 or 1 parameters."
        raise TypeError(msg)

    ((name, p),) = tuple(sig.parameters.items())
    if name == "svcs_container":
        return True

    if (annot := p.annotation) is Container or annot == "svcs.Container":
        return True

    return False
