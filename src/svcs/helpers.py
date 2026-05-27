import dataclasses
import inspect

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from svcs import Container
from svcs.exceptions import ServiceNotFoundError


_T = TypeVar("_T")


def autowire(fn_or_cls: Callable[..., _T]) -> Callable[[Container], _T]:
    """

    Return a wrapper that autowires dependencies from a container.


    The returned wrapper resolves dependencies based on type annotations

    of the wrapped callable's parameters, retrieving them from the
    provided container.


    Positional-only parameters are always resolved from the container.

    Keyword parameters with type annotations are resolved from the

    container, but if a parameter has a default value and the service

    is not found in the container, the default value is used instead
    of raising an error.


    Args:
        fn_or_cls:

          A callable (function or class) whose parameters will be

          autowired based on their type annotations.


    Returns:

        A wrapper function that accepts a container and returns the

        result of calling the original callable with dependencies

        resolved from that container.


    Autowiring a function using decorator notation:

    .. doctest::

        >>> from svcs import Container, Registry
        >>> class Service:
        ...     def __init__(self, name: str) -> None:
        ...         self.name = name
        >>> @autowire
        ... def build_label(svc: Service, suffix: int = 42) -> str:
        ...     return f"{svc.name}{suffix}"
        >>> registry = Registry()
        >>> registry.register_value(Service, Service("api"))
        >>> registry.register_factory(str, build_label)
        >>> with Container(registry) as container:
        ...     container.get(str)
        'api42'


    Autowiring a class:

    .. doctest::

        >>> from svcs import Container, Registry
        >>> class Service:
        ...     def __init__(self, name: str) -> None:
        ...         self.name = name
        >>> class Handler:
        ...     def __init__(self, svc: Service, prefix: str = "svc:") -> None:
        ...         self.svc = svc
        ...         self.prefix = prefix
        >>> registry = Registry()
        >>> registry.register_value(Service, Service("api"))
        >>> registry.register_factory(Handler, autowire(Handler))
        >>> with Container(registry) as container:
        ...     handler = container.get(Handler)
        ...     (handler.svc.name, handler.prefix)
        ('api', 'svc:')



    ..  versionadded:: 25.2.0

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

            if param.kind == param.POSITIONAL_ONLY:
                resolved = svcs_container.get(annotation)

                posargs.append(resolved)
                continue

            try:
                kwargs[name] = svcs_container.get(annotation)
            except ServiceNotFoundError:
                if param.default is param.empty:
                    raise

        return fn_or_cls(*posargs, **kwargs)

    return wrapper


def aautowire(
    fn_or_cls: Callable[..., _T],
) -> Callable[[Container], Awaitable[_T]]:
    """

    Return an async wrapper that autowires dependencies from a container.


    Like :func:`autowire`, but dependencies are resolved with

    :meth:`svcs.Container.aget` and therefore support async factories.


    Also works with synchronous services, so in an async application, just

    use this.


    ..  versionadded:: 25.2.0

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

            if param.kind == param.POSITIONAL_ONLY:
                resolved = await svcs_container.aget(annotation)

                posargs.append(resolved)
                continue

            try:
                kwargs[name] = await svcs_container.aget(annotation)
            except ServiceNotFoundError:
                if param.default is param.empty:
                    raise

        if is_async_fn:
            return await fn_or_cls(*posargs, **kwargs)  # type: ignore[no-any-return,misc]  # ty:ignore[invalid-await]

        return fn_or_cls(*posargs, **kwargs)

    return wrapper
