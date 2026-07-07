# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import dataclasses
import inspect

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from ._core import Container, _robust_signature
from .exceptions import ServiceNotFoundError


_T = TypeVar("_T")


def _lazy_signature(
    fn_or_cls: Callable[..., Any],
) -> Callable[[], inspect.Signature]:
    """
    Return a callable that resolves and caches the signature of *fn_or_cls* on
    first use.

    This allows autowire to work with (eventually resolvable) forward
    references.
    """
    cache: inspect.Signature | None = None

    def get_signature() -> inspect.Signature:
        nonlocal cache

        if not cache:
            sig = _robust_signature(fn_or_cls)
            if sig is None:
                msg = f"Cannot determine the signature of {fn_or_cls!r}."
                raise TypeError(msg)

            cache = sig

        return cache

    return get_signature


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

    .. warning::
        Do **not** decorate classes at definition time!
        Decorating a class using ``@autowire`` notation replaces the class
        with the autowire factory, so its name suddenly refers to a function,
        not a type.

        Wrap the class only at register time.

    .. versionadded:: 26.1.0
    """
    get_signature = _lazy_signature(fn_or_cls)

    def wrapper(svcs_container: Container) -> _T:
        sig = get_signature()

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
            except ServiceNotFoundError as e:
                # Only fall back to the default for this parameter's own
                # missing service. A miss for a different type means a
                # registered factory failed to resolve its own dependency
                # -- don't mask that.
                if param.default is param.empty or e.args[0] is not annotation:
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
    :meth:`svcs.Container.aget`, the returned factory is async, and
    *fn_or_cls* is awaited if it's a coroutine function.

    It also works with synchronous callables and services, so in an async
    application, just use this.

    .. versionadded:: 26.1.0
    """
    get_signature = _lazy_signature(fn_or_cls)
    is_async_fn = inspect.iscoroutinefunction(fn_or_cls)

    async def wrapper(svcs_container: Container) -> _T:
        sig = get_signature()

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
            except ServiceNotFoundError as e:
                # Only fall back to the default for this parameter's own
                # missing service. A miss for a different type means a
                # registered factory failed to resolve its own dependency
                # -- don't mask that.
                if param.default is param.empty or e.args[0] is not annotation:
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
