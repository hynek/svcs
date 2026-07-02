# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import dataclasses
import inspect

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from ._core import Container
from .exceptions import ServiceNotFoundError


_T = TypeVar("_T")


def autowire(fn_or_cls: Callable[..., _T]) -> Callable[[Container], _T]:
    """
    Return a factory that resolves the dependencies of *fn_or_cls* from a
    container, based on its type annotations.

    The returned factory takes a :class:`svcs.Container`, resolves every
    annotated parameter of *fn_or_cls* from it, and calls *fn_or_cls* with
    the resolved services.

    If a service is not found in the container and the parameter has a
    default value, the default is used instead of raising an error.

    Variadic parameters (``*args`` and ``**kwargs``) are ignored and
    :class:`dataclasses.InitVar` annotations are unwrapped.

    Args:
        fn_or_cls:
            A callable (function or class) whose parameters will be
            autowired based on their type annotations.

    Returns:
        A factory that takes a container and returns the result of calling
        *fn_or_cls* with the resolved dependencies.

    Autowiring a function using decorator notation:

    .. doctest::

        >>> import svcs

        >>> class Service:
        ...     def __init__(self, name: str) -> None:
        ...         self.name = name

        >>> @svcs.autowire
        ... def build_label(svc: Service, suffix: int = 42) -> str:
        ...     return f"{svc.name}{suffix}"

        >>> registry = svcs.Registry()
        >>> registry.register_value(Service, Service("api"))
        >>> registry.register_factory(str, build_label)

        >>> with svcs.Container(registry) as container:
        ...     container.get(str)
        'api42'

    Autowiring a class:

    .. doctest::

        >>> class Handler:
        ...     def __init__(self, svc: Service, prefix: str = "svc:") -> None:
        ...         self.svc = svc
        ...         self.prefix = prefix

        >>> registry = svcs.Registry()
        >>> registry.register_value(Service, Service("api"))
        >>> registry.register_factory(Handler, svcs.autowire(Handler))

        >>> with svcs.Container(registry) as container:
        ...     handler = container.get(Handler)
        ...     (handler.svc.name, handler.prefix)
        ('api', 'svc:')

    .. versionadded:: 26.1.0
    """
    sig = inspect.signature(fn_or_cls, follow_wrapped=False, eval_str=True)

    def wrapper(svcs_container: Container) -> _T:
        posargs: list[Any] = []
        kwargs: dict[str, Any] = {}

        for name, param in sig.parameters.items():
            # Skip variadic parameters (*args, **kwargs)
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue

            annotation = param.annotation
            # Unwrap InitVar[T] to get T
            if isinstance(annotation, dataclasses.InitVar):
                annotation = annotation.type

            try:
                resolved = svcs_container.get(annotation)
            except ServiceNotFoundError:
                if param.default is param.empty:
                    raise
                resolved = param.default

            if param.kind == param.POSITIONAL_ONLY:
                posargs.append(resolved)
                continue

            kwargs[name] = resolved

        return fn_or_cls(*posargs, **kwargs)

    return wrapper


def aautowire(
    fn_or_cls: Callable[..., _T],
) -> Callable[[Container], Awaitable[_T]]:
    """
    Like :func:`autowire`, but dependencies are resolved with
    :meth:`svcs.Container.aget` and *fn_or_cls* is awaited if it's a
    coroutine function, so both may be asynchronous.

    It also works with synchronous callables and services, so in an async
    application, just use this.

    .. versionadded:: 26.1.0
    """
    sig = inspect.signature(fn_or_cls, follow_wrapped=False, eval_str=True)
    is_async_fn = inspect.iscoroutinefunction(fn_or_cls)

    async def wrapper(svcs_container: Container) -> _T:
        posargs: list[Any] = []
        kwargs: dict[str, Any] = {}

        for name, param in sig.parameters.items():
            # Skip variadic parameters (*args, **kwargs)
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue

            annotation = param.annotation
            # Unwrap InitVar[T] to get T
            if isinstance(annotation, dataclasses.InitVar):
                annotation = annotation.type

            try:
                resolved = await svcs_container.aget(annotation)
            except ServiceNotFoundError:
                if param.default is param.empty:
                    raise
                resolved = param.default

            if param.kind == param.POSITIONAL_ONLY:
                posargs.append(resolved)
                continue

            kwargs[name] = resolved

        if is_async_fn:
            return await fn_or_cls(*posargs, **kwargs)  # type: ignore[no-any-return,misc]  # ty: ignore[invalid-await]

        return fn_or_cls(*posargs, **kwargs)

    return wrapper
