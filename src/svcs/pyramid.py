# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from typing import Any, Protocol, overload

import attrs

from pyramid.config import Configurator
from pyramid.registry import Registry
from pyramid.request import Request
from pyramid.response import Response
from pyramid.threadlocal import get_current_registry, get_current_request

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


def svcs_from(request: Request | None = None) -> svcs.Container:
    """
    Get the current container either from *request* or from thread locals.

    Args:
        request: If None, thread locals are used.
    """
    if request is None:
        request = get_current_request()

    return getattr(request, _KEY_CONTAINER)  # type: ignore[no-any-return]


def get_registry(rh: PyramidRegistryHaver | None = None) -> svcs.Registry:
    """
    Get the registry from *rh* or thread locals.

    Args:
        rh: If None, thread locals are used.
    """
    registry = rh.registry if rh else get_current_registry()

    return registry[_KEY_REGISTRY]  # type: ignore[no-any-return]


def init(
    config: Configurator,
    *,
    registry: svcs.Registry | None = None,
    tween_under: Any = None,
    tween_over: Any = None,
) -> None:
    """
    Configure *config* to work with *svcs*.

    *svcs* uses a :term:`tween` to manage the life cycle of the container. You
    can affect its position by passing *tween_under* and *tween_over*.

    .. _Tween: https://docs.pylonsproject.org/projects/pyramid/en/main/glossary.html#term-tween

    Args:
        config: Pyramid configurator object.

        registry:
            A custom *svcs* registry to use. If None, a new one is created.

        tween_under:
            Passed unchanged to :meth:`pyramid.config.Configurator.add_tween()`
            as *under*.

        tween_over:
            Passed unchanged to :meth:`pyramid.config.Configurator.add_tween()`
            as *over*.
    """
    config.registry[_KEY_REGISTRY] = registry or svcs.Registry()

    config.add_tween(
        "svcs.pyramid.ServicesTween", over=tween_over, under=tween_under
    )


@attrs.define
class ServicesTween:
    """
    Handle *svcs* container life cycle for a Pyramid request.
    """

    handler: Callable[[Request], Response]
    registry: Registry

    def __call__(self, request: Request) -> Response:
        def make_container(request: Request) -> svcs.Container:
            con = svcs.Container(self.registry[_KEY_REGISTRY])
            request.add_finished_callback(lambda _: con.close())

            return con

        request.set_property(make_container, _KEY_CONTAINER, reify=True)
        return self.handler(request)


def register_factory(
    config: PyramidRegistryHaver,
    svc_type: type,
    factory: Callable,
    *,
    enter: bool = True,
    ping: Callable | None = None,
    on_registry_close: Callable | None = None,
) -> None:
    """
    Same as :meth:`svcs.Registry.register_factory()`, but uses registry on
    *config*.
    """
    config.registry[_KEY_REGISTRY].register_factory(
        svc_type,
        factory,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
    )


def register_value(
    config: PyramidRegistryHaver,
    svc_type: type,
    value: object,
    *,
    enter: bool = False,
    ping: Callable | None = None,
    on_registry_close: Callable | None = None,
) -> None:
    """
    Same as :meth:`svcs.Registry.register_value()`, but uses registry on
    *config*.
    """
    config.registry[_KEY_REGISTRY].register_value(
        svc_type,
        value,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
    )


def close_registry(rh: PyramidRegistryHaver) -> None:
    """
    Close the registry on *rh*, if present.

    Ideal for :func:`atexit.register()` handlers.

    Args:
        rh: An object that carries a :class:`pyramid.registry.Registry`.
    """
    with suppress(KeyError):
        get_registry(rh).close()


class PyramidRegistryHaver(Protocol):
    """
    An object with a :class:`pyramid.registry.Registry` as a ``registry``
    attribute. For example a :class:`~pyramid.config.Configurator` or an
    application.
    """

    registry: dict[str, Any]


def get_pings(request: Request) -> list[svcs.ServicePing]:
    """
    Like :meth:`svcs.Container.get_pings()`, but uses container on *request*.

    See Also:
        :ref:`pyramid-health`
    """
    return svcs_from(request).get_pings()


def get_abstract(request: Request, *svc_types: type) -> Any:
    """
    Same as :meth:`svcs.Container.get_abstract()`, but uses container from
    *request*.
    """
    return svcs_from(request).get(*svc_types)


@overload
def get(request: Request, svc_type: type[T1], /) -> T1: ...


@overload
def get(
    request: Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    /,
) -> tuple[T1, T2]: ...


@overload
def get(
    request: Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    /,
) -> tuple[T1, T2, T3]: ...


@overload
def get(
    request: Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    /,
) -> tuple[T1, T2, T3, T4]: ...


@overload
def get(
    request: Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    /,
) -> tuple[T1, T2, T3, T4, T5]: ...


@overload
def get(
    request: Request,
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    svc_type6: type[T6],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6]: ...


@overload
def get(
    request: Request,
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
def get(
    request: Request,
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
def get(
    request: Request,
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
def get(
    request: Request,
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


def get(request: Request, *svc_types: type) -> object:
    """
    Same as :meth:`svcs.Container.get()`, but uses thread locals to find the
    current request.
    """
    return svcs_from(request).get(*svc_types)
