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
from typing import Any, AsyncGenerator, Awaitable, Generator, TypeVar, overload

import attrs

from .exceptions import ServiceNotFoundError


log = logging.getLogger(__name__)

if sys.version_info < (3, 10):

    def anext(gen: AsyncGenerator) -> Any:
        return gen.__anext__()


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
    """
    A service health check as returned by :meth:`svcs.Container.get_pings`.

    Attributes:
        name: A fully-qualified name of the service type.

        is_async: Whether the service needs to be pinged using :meth:`aping`.

    See also:
        :ref:`health`
    """

    name: str
    is_async: bool
    _svc_type: type
    _ping: Callable
    _container: Container

    def ping(self) -> None:
        """
        Instantiate the service, schedule its cleanup, and call its ping
        method.
        """
        svc: Any = self._container.get(self._svc_type)
        self._ping(svc)

    async def aping(self) -> None:
        """
        Same as :meth:`ping` but instantiate and/or ping asynchronously, if
        necessary.

        Also works with synchronous services, so in an async application, just
        use this.
        """
        svc: Any = await self._container.aget(self._svc_type)
        if iscoroutinefunction(self._ping):
            await self._ping(svc)
        else:
            self._ping(svc)


@attrs.define
class Registry:
    """
    A central registry of recipes for creating services.

    An instance of this should live as long as your application does.

    Also works as a context manager that runs ``on_registry_close`` hooks on
    exit:

    .. doctest::

        >>> import svcs
        >>> with svcs.Registry() as reg:
        ...     reg.register_value(
        ...         int, 42,
        ...         on_registry_close=lambda: print("closed!")
        ...     )
        closed!

    ``async with`` is also supported.
    """

    _services: dict[type, RegisteredService] = attrs.Factory(dict)
    _on_close: list[tuple[str, Callable | Awaitable]] = attrs.Factory(list)

    def __repr__(self) -> str:
        return f"<svcs.Registry(num_services={len(self._services)})>"

    def __contains__(self, svc_type: type) -> bool:
        """
        Check whether this registry knows how to create *svc_type*:

        .. doctest::

            >>> reg = svcs.Registry()
            >>> reg.register_value(int, 42)
            >>> int in reg
            True
            >>> str in reg
            False
        """
        return svc_type in self._services

    def __enter__(self) -> Registry:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    async def __aenter__(self) -> Registry:
        return self

    async def __aexit__(
        self, exc_type: Any, exc_val: Any, exc_tb: Any
    ) -> None:
        await self.aclose()

    def register_factory(
        self,
        svc_type: type,
        factory: Callable,
        *,
        ping: Callable | None = None,
        on_registry_close: Callable | Awaitable | None = None,
    ) -> None:
        """
        Register *factory* to be used when asked for a *svc_type*.

        Repeated registrations overwrite previous ones, but the
        *on_registry_close* hooks are run all together when the registry is
        closed.

        Args:
            svc_type: The type of the service to register.

            factory: A callable that is used to instantiated *svc_type* if
                asked. If it's a generator, a cleanup is registered after
                instantiation.

                Can also be an async callable or an async generator.

                If *factory* takes a first argument called ``svcs_container``
                or the first argument (of any name) is annotated as being
                :class:`svcs.Container`, the container instance that is
                instantiating the service is passed into the factory as the
                first positional argument.

            ping: A callable that marks the service as having a health check.

                .. seealso::
                    :meth:`Container.get_pings` and :class:`ServicePing`.

            on_registry_close: A callable that is called when the
                :meth:`svcs.Registry.close()` method is called.

                Can also be an async callable or an
                :class:`collections.abc.Awaitable`, then
                :meth:`svcs.Registry.aclose()` must be called.
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
        Syntactic sugar for::

           register_factory(
               svc_type,
               lambda: value,
               ping=ping,
               on_registry_close=on_registry_close
           )
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
        Clear registrations and run synchronous *on_registry_close* hooks.

        Async hooks are *not* awaited and a warning is raised

        Errors are logged at warning level, but otherwise ignored.
        """
        for name, oc in reversed(self._on_close):
            if iscoroutinefunction(oc) or isawaitable(oc):
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
                oc()  # type: ignore[operator]
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
        Clear registrations and run all *on_registry_close* hooks.

        Errors are logged at warning level, but otherwise ignored.

        Also works with synchronous services, so in an async application, just
        use this.
        """
        for name, oc in reversed(self._on_close):
            try:
                if iscoroutinefunction(oc):
                    oc = oc()  # noqa: PLW2901

                if isawaitable(oc):
                    log.debug("async closing %r", name)
                    await oc
                    log.debug("async closed %r", name)
                else:
                    log.debug("closing %r", name)
                    oc()  # type: ignore[operator]
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
    try:
        sig = inspect.signature(factory)
    except Exception:  # noqa: BLE001
        return False

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


T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")
T4 = TypeVar("T4")
T5 = TypeVar("T5")
T6 = TypeVar("T6")
T7 = TypeVar("T7")
T8 = TypeVar("T8")
T9 = TypeVar("T9")
T10 = TypeVar("T10")


@attrs.define
class Container:
    """
    A per-context container for instantiated services and cleanups.

    The instance of this should live as long as a request or a task.

    Also works as a context manager that runs clean ups on exit:

    .. doctest::

        >>> reg = svcs.Registry()
        >>> def factory() -> str:
        ...     yield "Hello World"
        ...     print("Cleaned up!")
        >>> reg.register_factory(str, factory)

        >>> with svcs.Container(reg) as con:
        ...     _ = con.get(str)
        Cleaned up!

    Attributes:

        registry: The :class:`Registry` instance that this container uses for
           service type lookup.
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

    def __contains__(self, svc_type: type) -> bool:
        """
        Check whether this container has a cached instance of *svc_type*.
        """
        return svc_type in self._instantiated

    def __enter__(self) -> Container:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    async def __aenter__(self) -> Container:
        return self

    async def __aexit__(
        self, exc_type: Any, exc_val: Any, exc_tb: Any
    ) -> None:
        await self.aclose()

    def forget_about(self, svc_type: type) -> None:
        """
        Forget cached instances of *svc_type* if there are any.
        """
        with suppress(KeyError):
            del self._instantiated[svc_type]

    def close(self) -> None:
        """
        Run all registered *synchronous* cleanups.

        Async closes are *not* awaited and a warning is raised.

        Errors are logged at warning level, but otherwise ignored.
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

        Errors are logged at warning level, but otherwise ignored.

        Also works with synchronous services, so in an async application, just
        use this.
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
        Return all services that have defined a *ping* and bind them to this
        container.

        Returns:
            A sequence of services that have registered a ping callable.
        """
        return [
            ServicePing(
                rs.name,
                rs.is_async or iscoroutinefunction(rs.ping),
                rs.svc_type,
                rs.ping,
                self,
            )
            for rs in self.registry._services.values()
            if rs.ping is not None
        ]

    def get_abstract(self, *svc_types: type) -> Any:
        """
        Like :meth:`get` but is annotated to return :data:`typing.Any` which
        allows it to be used with abstract types like :class:`typing.Protocol`
        or :mod:`abc` classes.

        Note:
             See https://github.com/python/mypy/issues/4717 why this is
             necessary.
        """
        return self.get(*svc_types)

    async def aget_abstract(self, *svc_types: type) -> Any:
        """
        Same as :meth:`get_abstract` but instantiates asynchronously, if
        necessary.

        Also works with synchronous services, so in an async application, just
        use this.
        """
        return await self.aget(*svc_types)

    @overload
    def get(self, svc_type: type[T1], /) -> T1:
        ...

    @overload
    def get(
        self, svc_type1: type[T1], svc_type2: type[T2], /
    ) -> tuple[T1, T2]:
        ...

    @overload
    def get(
        self, svc_type1: type[T1], svc_type2: type[T2], svc_type3: type[T3], /
    ) -> tuple[T1, T2, T3]:
        ...

    @overload
    def get(
        self,
        svc_type1: type[T1],
        svc_type2: type[T2],
        svc_type3: type[T3],
        svc_type4: type[T4],
        /,
    ) -> tuple[T1, T2, T3, T4]:
        ...

    @overload
    def get(
        self,
        svc_type1: type[T1],
        svc_type2: type[T2],
        svc_type3: type[T3],
        svc_type4: type[T4],
        svc_type5: type[T5],
        /,
    ) -> tuple[T1, T2, T3, T4, T5]:
        ...

    @overload
    def get(
        self,
        svc_type1: type[T1],
        svc_type2: type[T2],
        svc_type3: type[T3],
        svc_type4: type[T4],
        svc_type5: type[T5],
        svc_type6: type[T6],
        /,
    ) -> tuple[T1, T2, T3, T4, T5, T6]:
        ...

    @overload
    def get(
        self,
        svc_type1: type[T1],
        svc_type2: type[T2],
        svc_type3: type[T3],
        svc_type4: type[T4],
        svc_type5: type[T5],
        svc_type6: type[T6],
        svc_type7: type[T7],
        /,
    ) -> tuple[T1, T2, T3, T4, T5, T6, T7]:
        ...

    @overload
    def get(
        self,
        svc_type1: type[T1],
        svc_type2: type[T2],
        svc_type3: type[T3],
        svc_type4: type[T4],
        svc_type5: type[T5],
        svc_type6: type[T6],
        svc_type7: type[T7],
        svc_type8: type[T8],
        /,
    ) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8]:
        ...

    @overload
    def get(
        self,
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
    ) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9]:
        ...

    @overload
    def get(
        self,
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
    ) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9, T10]:
        ...

    def get(self, *svc_types: type) -> object:
        """
        Get services of *svc_types*.

        Instantiate them if necessary and register their cleanup.

        Returns:
             ``svc_types[0]`` | ``tuple[*svc_types]``: If one service is
             requested, it's returned directly. If multiple are requested, a
             tuple of services is returned.
        """
        rv = []
        for svc_type in svc_types:
            if (
                svc := self._instantiated.get(svc_type, attrs.NOTHING)
            ) is not attrs.NOTHING:
                rv.append(svc)
                continue

            rs = self.registry.get_registered_service_for(svc_type)
            if rs.is_async:
                msg = "Please use `aget()` for async factories."
                raise TypeError(msg)

            svc = rs.factory(self) if rs.takes_container else rs.factory()

            if isinstance(svc, Generator):
                self._on_close.append((rs.name, svc))
                svc = next(svc)

            self._instantiated[svc_type] = svc

            rv.append(svc)

        if len(rv) == 1:
            return rv[0]

        return rv

    @overload
    async def aget(self, svc_type: type[T1], /) -> T1:
        ...

    @overload
    async def aget(
        self, svc_type1: type[T1], svc_type2: type[T2], /
    ) -> tuple[T1, T2]:
        ...

    @overload
    async def aget(
        self, svc_type1: type[T1], svc_type2: type[T2], svc_type3: type[T3], /
    ) -> tuple[T1, T2, T3]:
        ...

    @overload
    async def aget(
        self,
        svc_type1: type[T1],
        svc_type2: type[T2],
        svc_type3: type[T3],
        svc_type4: type[T4],
        /,
    ) -> tuple[T1, T2, T3, T4]:
        ...

    @overload
    async def aget(
        self,
        svc_type1: type[T1],
        svc_type2: type[T2],
        svc_type3: type[T3],
        svc_type4: type[T4],
        svc_type5: type[T5],
        /,
    ) -> tuple[T1, T2, T3, T4, T5]:
        ...

    @overload
    async def aget(
        self,
        svc_type1: type[T1],
        svc_type2: type[T2],
        svc_type3: type[T3],
        svc_type4: type[T4],
        svc_type5: type[T5],
        svc_type6: type[T6],
        /,
    ) -> tuple[T1, T2, T3, T4, T5, T6]:
        ...

    @overload
    async def aget(
        self,
        svc_type1: type[T1],
        svc_type2: type[T2],
        svc_type3: type[T3],
        svc_type4: type[T4],
        svc_type5: type[T5],
        svc_type6: type[T6],
        svc_type7: type[T7],
        /,
    ) -> tuple[T1, T2, T3, T4, T5, T6, T7]:
        ...

    @overload
    async def aget(
        self,
        svc_type1: type[T1],
        svc_type2: type[T2],
        svc_type3: type[T3],
        svc_type4: type[T4],
        svc_type5: type[T5],
        svc_type6: type[T6],
        svc_type7: type[T7],
        svc_type8: type[T8],
        /,
    ) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8]:
        ...

    @overload
    async def aget(
        self,
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
    ) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9]:
        ...

    @overload
    async def aget(
        self,
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
    ) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9, T10]:
        ...

    async def aget(self, *svc_types: type) -> object:
        """
        Same as :meth:`get` but instantiates asynchronously, if necessary.

        Also works with synchronous services, so in an async application, just
        use this.
        """
        rv = []
        for svc_type in svc_types:
            if (
                svc := self._instantiated.get(svc_type, attrs.NOTHING)
            ) is not attrs.NOTHING:
                rv.append(svc)
                continue

            rs = self.registry.get_registered_service_for(svc_type)
            svc = rs.factory()

            if isinstance(svc, AsyncGenerator):
                self._on_close.append((rs.name, svc))
                svc = await anext(svc)
            elif isawaitable(svc):
                svc = await svc

            self._instantiated[rs.svc_type] = svc

            rv.append(svc)

        if len(rv) == 1:
            return rv[0]

        return rv
