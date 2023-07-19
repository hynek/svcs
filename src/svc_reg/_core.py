from __future__ import annotations

import logging
import warnings

from collections.abc import Callable
from contextlib import suppress
from typing import Any, AsyncGenerator, Generator

import attrs

from .exceptions import ServiceNotFoundError


log = logging.getLogger(__name__)


@attrs.define
class Container:
    """
    A per-context container for instantiated services & cleanups.
    """

    registry: Registry
    instantiated: dict[type, object] = attrs.Factory(dict)
    cleanups: list[tuple[RegisteredService, Generator]] = attrs.Factory(list)
    async_cleanups: list[
        tuple[RegisteredService, AsyncGenerator]
    ] = attrs.Factory(list)

    def __repr__(self) -> str:
        return (
            f"<Container(instantiated={len(self.instantiated)}, "
            f"cleanups={len(self.cleanups)}, "
            f"async_cleanups={len(self.async_cleanups)})>"
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
            self.async_cleanups.append((rs, svc))
            svc = await svc.__anext__()
        else:
            svc = await svc  # type: ignore[misc]

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
        """
        while self.cleanups:
            rs, gen = self.cleanups.pop()
            try:
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
        self.close()

        while self.async_cleanups:
            rs, gen = self.async_cleanups.pop()
            try:
                await gen.__anext__()

                warnings.warn(
                    f"clean up for {rs!r} didn't stop iterating", stacklevel=1
                )

            except StopAsyncIteration:  # noqa: PERF203
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


@attrs.frozen
class ServicePing:
    _container: Container
    _rs: RegisteredService

    def ping(self) -> None:
        svc = self._container.get(self._rs.svc_type)
        self._rs.ping(svc)  # type: ignore[misc]

    @property
    def name(self) -> str:
        return self._rs.name


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
