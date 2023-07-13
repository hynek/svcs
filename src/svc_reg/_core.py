from __future__ import annotations

import asyncio
import logging

from collections.abc import Callable
from contextlib import suppress
from typing import Any

import attrs


log = logging.getLogger(__name__)


class ServiceNotFoundError(Exception):
    """
    Raised when a service type is not registered.
    """


@attrs.define
class Container:
    """
    A per-context container for instantiated services & cleanups.
    """

    registry: Registry
    instantiated: dict[type, object] = attrs.Factory(dict)
    cleanups: list[tuple[RegisteredService, object]] = attrs.Factory(list)
    async_cleanups: list[tuple[RegisteredService, object]] = attrs.Factory(
        list
    )

    def __repr__(self) -> str:
        return (
            f"<Container(instantiated={len(self.instantiated)}, "
            f"cleanups={len(self.cleanups)}, "
            f"async_cleanups={len(self.async_cleanups)}>"
        )

    def get(self, svc_type: type) -> Any:
        """
        Get an instance of *svc_type*.

        Instantiate it if necessary and register its cleanup.

        Returns:
             Any until https://github.com/python/mypy/issues/4717 is fixed.
        """
        if (svc := self._get_instance(svc_type)) is not None:
            return svc

        rs = self.registry.get_registered_service_for(svc_type)
        svc = rs.factory()
        self._add_instance(rs, svc)

        return svc

    def _add_instance(self, rs: RegisteredService, svc: object) -> None:
        self.instantiated[rs.svc_type] = svc
        self.add_cleanup(rs, svc)

    def _get_instance(self, svc_type: type) -> object | None:
        """
        If present, return the cached instance of *svc_type*.
        """
        return self.instantiated.get(svc_type)

    def add_cleanup(self, rs: RegisteredService, svc: object) -> bool:
        """
        Add a cleanup function for *svc* if *rs* has one without remembering
        the service itself.

        Return:
            True if a cleanup was added, False otherwise.
        """
        if not rs.cleanup:
            return False

        if asyncio.iscoroutinefunction(rs.cleanup):
            self.async_cleanups.append((rs, svc))
        else:
            self.cleanups.append((rs, svc))

        return True

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
            rs, svc = self.cleanups.pop()
            try:
                rs.cleanup(svc)  # type: ignore[misc]
            except Exception:  # noqa: PERF203, BLE001
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
            rs, svc = self.async_cleanups.pop()
            try:
                await rs.cleanup(svc)  # type: ignore[misc]
            except Exception:  # noqa: PERF203, BLE001
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
    cleanup: Callable | None = attrs.field(hash=False)
    ping: Callable | None = attrs.field(hash=False)

    @property
    def name(self) -> str:
        return self.svc_type.__qualname__

    def __repr__(self) -> str:
        return (
            f"<RegisteredService(svc_type={ self.svc_type.__module__ }."
            f"{ self.svc_type.__qualname__ }, "
            f"has_cleanup={ self.cleanup is not None}, "
            f"has_ping={ self.ping is not None})>"
        )


@attrs.frozen
class ServicePing:
    _container: Container
    _rs: RegisteredService

    def ping(self) -> None:
        svc = self._rs.factory()
        self._container.add_cleanup(self._rs, svc)
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
        cleanup: Callable | None = None,
        ping: Callable | None = None,
    ) -> None:
        self.services[svc_type] = RegisteredService(
            svc_type, factory, cleanup, ping
        )

    def register_value(
        self,
        svc_type: type,
        instance: object,
        *,
        cleanup: Callable | None = None,
        ping: Callable | None = None,
    ) -> None:
        self.register_factory(
            svc_type, lambda: instance, cleanup=cleanup, ping=ping
        )

    def get_registered_service_for(self, svc_type: type) -> RegisteredService:
        try:
            return self.services[svc_type]
        except KeyError:
            raise ServiceNotFoundError(svc_type) from None
