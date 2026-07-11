# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import dataclasses
import inspect

from collections.abc import Awaitable, Callable, Iterator
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


def _reject_bare_generator(fn_or_cls: Callable[..., Any]) -> None:
    """
    Raise TypeError if *fn_or_cls* is a bare (async) generator function.

    The autowire wrapper is a plain function, so the registry's automatic
    context-manager conversion of generator factories never kicks in and
    their cleanup would be silently lost.
    """
    if inspect.isgeneratorfunction(fn_or_cls):
        msg = (
            f"Cannot autowire the generator function {fn_or_cls!r}: its "
            f"cleanup would be lost. Decorate it with "
            f"contextlib.contextmanager instead."
        )
        raise TypeError(msg)

    if inspect.isasyncgenfunction(fn_or_cls):
        msg = (
            f"Cannot autowire the async generator function {fn_or_cls!r}: "
            f"its cleanup would be lost. Decorate it with "
            f"contextlib.asynccontextmanager instead."
        )
        raise TypeError(msg)


def _wireable_params(
    sig: inspect.Signature,
) -> Iterator[tuple[str, inspect.Parameter, Any]]:
    """
    Yield the ``(name, parameter, annotation)`` triples of *sig* that
    autowire should resolve from a container.
    """
    for name, param in sig.parameters.items():
        # skip variadic parameters (``*args`` and ``**kwargs``)
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue

        annotation = param.annotation
        if isinstance(annotation, dataclasses.InitVar):
            annotation = annotation.type

        if annotation is param.empty and param.default is param.empty:
            msg = (
                f"Cannot autowire parameter {name!r}: it has no type "
                f"annotation and no default."
            )
            raise TypeError(msg)

        yield name, param, annotation


def _default_or_raise(
    param: inspect.Parameter, annotation: Any, exc: ServiceNotFoundError
) -> Any:
    """
    Return *param*'s default when its own service is missing, else re-raise.
    """
    # Only fall back for a miss of *annotation* itself. A miss for a different
    # type means a registered factory failed to resolve its own dependency,
    # which must not be masked by the default.
    if param.default is param.empty or exc.args[0] is not annotation:
        raise exc

    return param.default


def autowire(fn_or_cls: Callable[..., _T]) -> Callable[[Container], _T]:
    """
    Return a factory that resolves the dependencies of *fn_or_cls* from
    a container, based on its type annotations.

    The returned factory takes a :class:`svcs.Container`, resolves every
    annotated parameter of *fn_or_cls* from it, and calls *fn_or_cls* with the
    resolved services.

    If a service is not found in the container and the parameter has a default
    value, the default is used instead of raising an error.

    Variadic parameters (``*args`` and ``**kwargs``) are ignored and
    :class:`dataclasses.InitVar` annotations are unwrapped.

    Factories that return context managers are entered and cleaned up as usual.
    Bare generator factories are rejected, because their cleanup would be lost.
    Decorate them with :func:`~contextlib.contextmanager` instead.

    Args:
        fn_or_cls:
            A callable (function or class) whose parameters will be
            autowired based on their type annotations.

    Returns:
        A factory that takes a container and returns the result of calling
        *fn_or_cls* with the resolved dependencies.

    Raises:
        TypeError:
            If a required parameter has neither a type annotation nor a
            default value.

        TypeError:
            If *fn_or_cls* is a bare generator function.

    .. warning::
        Do **not** decorate classes at definition time! Decorating a class
        using ``@autowire`` notation replaces the class with the autowire
        factory, so its name suddenly refers to a function, not a type.

        Wrap the class only at register time.

    .. versionadded:: 26.1.0
    """
    _reject_bare_generator(fn_or_cls)
    get_signature = _lazy_signature(fn_or_cls)

    def wrapper(svcs_container: Container) -> _T:
        posargs: list[Any] = []
        kwargs: dict[str, Any] = {}

        for name, param, annotation in _wireable_params(get_signature()):
            try:
                resolved = svcs_container.get(annotation)
            except ServiceNotFoundError as e:
                resolved = _default_or_raise(param, annotation, e)

            if param.kind == param.POSITIONAL_ONLY:
                posargs.append(resolved)
            else:
                kwargs[name] = resolved

        return fn_or_cls(*posargs, **kwargs)

    return wrapper


def aautowire(
    fn_or_cls: Callable[..., _T],
) -> Callable[[Container], Awaitable[_T]]:
    """
    Like :func:`autowire`, but dependencies are resolved with
    :meth:`svcs.Container.aget`, the returned factory is async, and the
    result of *fn_or_cls* is awaited if it's awaitable.

    It also works with synchronous callables and services, so in an async
    application, just use this.

    .. versionadded:: 26.1.0
    """
    _reject_bare_generator(fn_or_cls)
    get_signature = _lazy_signature(fn_or_cls)

    async def wrapper(svcs_container: Container) -> _T:
        posargs: list[Any] = []
        kwargs: dict[str, Any] = {}

        for name, param, annotation in _wireable_params(get_signature()):
            try:
                resolved = await svcs_container.aget(annotation)
            except ServiceNotFoundError as e:
                resolved = _default_or_raise(param, annotation, e)

            if param.kind == param.POSITIONAL_ONLY:
                posargs.append(resolved)
            else:
                kwargs[name] = resolved

        result = fn_or_cls(*posargs, **kwargs)
        # Mirror Container.aget's semantics: await anything awaitable, so
        # coroutine functions, partials, and instances with an async
        # __call__ all work.
        if inspect.isawaitable(result):
            result = await result

        return result  # pyright: ignore[reportReturnType]  # ty:ignore[invalid-return-type]

    return wrapper
