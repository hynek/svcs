# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast, overload

from flask import Flask, current_app, g, has_app_context
from flask.ctx import _AppCtxGlobals
from werkzeug.local import LocalProxy

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
    Container,
    Registry,
    ServicePing,
)


def svcs_from(g: _AppCtxGlobals = g) -> Container:
    """
    Get the current container from *g*.
    """
    if (con := g.get(_KEY_CONTAINER, None)) is None:
        con = Container(current_app.extensions[_KEY_REGISTRY])
        setattr(g, _KEY_CONTAINER, con)

    return con  # type: ignore[no-any-return]


def get_registry(app: Flask | None = None) -> Registry:
    """
    Get the registry from *app* or :obj:`flask.current_app`.

    Args:
        app: If None, :obj:`flask.current_app` is used.

    .. versionadded:: 23.21.0
       *app* can be None, in which case :obj:`flask.current_app` is used.
    """
    if app is None:
        app = current_app
    return app.extensions[_KEY_REGISTRY]  # type: ignore[no-any-return]


registry = cast(Registry, LocalProxy(get_registry))
container = cast(Container, LocalProxy(svcs_from))

FlaskAppT = TypeVar("FlaskAppT", bound=Flask)


def init_app(app: FlaskAppT, *, registry: Registry | None = None) -> FlaskAppT:
    """
    Initialize *app* for *svcs*.

    Creates a registry for you if you don't provide one.
    """
    app.extensions[_KEY_REGISTRY] = registry or Registry()
    app.teardown_appcontext(teardown)

    return app


def get_abstract(*svc_types: type) -> Any:
    """
    Same as :meth:`svcs.Container.get_abstract()`, but uses container on
    :obj:`flask.g`.
    """
    return get(*svc_types)


def register_factory(
    app: Flask,
    svc_type: type,
    factory: Callable,
    *,
    enter: bool = True,
    ping: Callable | None = None,
    on_registry_close: Callable | None = None,
) -> None:
    """
    Same as :meth:`svcs.Registry.register_factory()`, but uses registry on
    *app* that has been put there by :func:`init_app()`.
    """
    app.extensions[_KEY_REGISTRY].register_factory(
        svc_type,
        factory,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
    )


def register_value(
    app: Flask,
    svc_type: type,
    value: object,
    *,
    enter: bool = False,
    ping: Callable | None = None,
    on_registry_close: Callable | None = None,
) -> None:
    """
    Same as :meth:`svcs.Registry.register_value()`, but uses registry on *app*
    that has been put there by :func:`init_app()`.
    """
    app.extensions[_KEY_REGISTRY].register_value(
        svc_type,
        value,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
    )


def overwrite_factory(
    svc_type: type,
    factory: Callable,
    *,
    enter: bool = True,
    ping: Callable | None = None,
    on_registry_close: Callable | None = None,
) -> None:
    """
    Obtain the currently active container on ``g`` and overwrite the factory
    for *svc_type*.

    Afterwards resets the instantiation cache on ``g``.

    See Also:
        - :meth:`svcs.Registry.register_factory()`
        - :meth:`svcs.Container.close()`
    """
    container = svcs_from()
    container.registry.register_factory(
        svc_type,
        factory,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
    )
    container.close()


def overwrite_value(
    svc_type: type,
    value: object,
    *,
    enter: bool = True,
    ping: Callable | None = None,
    on_registry_close: Callable | None = None,
) -> None:
    """
    Obtain the currently active container on ``g`` and overwrite the value
    for *svc_type*.

    Afterwards resets the instantiation cache on ``g``.

    See Also:
        - :meth:`svcs.Registry.register_factory()`
        - :meth:`svcs.Container.close()`
    """
    container = svcs_from()
    container.registry.register_value(
        svc_type,
        value,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
    )
    container.close()


def get_pings() -> list[ServicePing]:
    """
    See :meth:`svcs.Container.get_pings()`.

    See Also:
        :ref:`flask-health`
    """
    return svcs_from(g).get_pings()


def teardown(exc: BaseException | None) -> None:
    """
    To be used with :meth:`flask.Flask.teardown_appcontext` that requires to
    take an exception.

    The app context is torn down after the response is sent.
    """
    if has_app_context() and (container := g.pop(_KEY_CONTAINER, None)):
        container.close()


def close_registry(app: Flask) -> None:
    """
    Close the registry on *app*, if present.
    """
    if reg := app.extensions.pop(_KEY_REGISTRY, None):
        reg.close()


@overload
def get(svc_type: type[T1], /) -> T1: ...


@overload
def get(svc_type1: type[T1], svc_type2: type[T2], /) -> tuple[T1, T2]: ...


@overload
def get(
    svc_type1: type[T1], svc_type2: type[T2], svc_type3: type[T3], /
) -> tuple[T1, T2, T3]: ...


@overload
def get(
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    /,
) -> tuple[T1, T2, T3, T4]: ...


@overload
def get(
    svc_type1: type[T1],
    svc_type2: type[T2],
    svc_type3: type[T3],
    svc_type4: type[T4],
    svc_type5: type[T5],
    /,
) -> tuple[T1, T2, T3, T4, T5]: ...


@overload
def get(
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


def get(*svc_types: type) -> object:
    """
    Same as :meth:`svcs.Container.get()`, but uses container on :obj:`flask.g`.
    """
    return svcs_from(g).get(*svc_types)
