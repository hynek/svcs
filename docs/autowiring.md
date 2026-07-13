# Autowiring

::: {versionadded} 26.1.0
:::

Autowiring is an optional technique that automatically resolves dependencies based on type annotations, eliminating the need to manually specify each dependency when invoking a function or instantiating a class.
This reduces boilerplate and makes your code more declarative.

The autowiring functions inject dependencies from a {class}`svcs.Container` directly into function or class parameters based on their type annotations.
This is particularly useful when you want to build factories or handlers that consume multiple services without explicitly passing them through each layer:

```python
>>> from dataclasses import dataclass
>>> from typing import NewType

>>> import svcs

>>> @dataclass
... class Database: ...

>>> @dataclass
... class Cache: ...

>>> registry = svcs.Registry()
>>> registry.register_factory(Database, Database)
>>> registry.register_factory(Cache, Cache)

>>> @dataclass
... class AppServices:
...     db: Database
...     cache: Cache

>>> # BEFORE: wire the dependencies by hand.
>>> BeforeAppServices = NewType("BeforeAppServices", AppServices)
>>> registry.register_factory(
...     BeforeAppServices,
...     lambda svcs_container: AppServices(
...         db=svcs_container.get(Database),
...         cache=svcs_container.get(Cache),
...     ),
... )

>>> # AFTER: the type annotations are enough.
>>> AfterAppServices = NewType("AfterAppServices", AppServices)
>>> registry.register_factory(AfterAppServices, svcs.autowire(AppServices))

>>> with svcs.Container(registry) as container:
...     before = container.get(BeforeAppServices)
...     after = container.get(AfterAppServices)

>>> # The resulting services look the same...
>>> before
AppServices(db=Database(), cache=Cache())
>>> after
AppServices(db=Database(), cache=Cache())
>>> before == after
True
>>> # but they are different instances...
>>> before is after
False
>>> # ... although their dependencies are shared.
>>> before.db is after.db
True
>>> before.cache is after.cache
True
```

Autowiring handles regular, positional-only, and keyword-only parameters, and ignores variadic ones (`*args` and `**kwargs`).
If a parameter cannot be resolved because the service has not been registered,
the default value is injected instead.

A parameter annotated as {class}`svcs.Container` receives the current container itself, so a factory can look up further services dynamically.
Autowiring only looks at type annotations, therefore injecting the container by naming an argument `svcs_container` does **not** work.

Factories that return context managers are entered and cleaned up as usual.
Bare generator factories, however, are rejected with a `TypeError`, because their cleanup would be lost.
Decorate them with {func}`~contextlib.contextmanager` or {func}`~contextlib.asynccontextmanager` instead.

::: {note}
For asynchronous resolution, {func}`svcs.aautowire` exists
and uses {meth}`svcs.Container.aget()` instead of {meth}`svcs.Container.get()`.
It supports both synchronous and asynchronous callables; therefore in async contexts you can always use {func}`svcs.aautowire`.
:::

Pros:

- **Less Boilerplate:** Dependencies are resolved automatically from type annotations.
- **Clear Intent:** Signatures still document required services.
- **Sensible Defaults:** Missing optional services fall back to parameter defaults.

Cons:

- **More Implicit:** Dependency lookup is less explicit than direct {meth}`svcs.Container.get()` calls.
- **Extra Indirection:** Wrapping and introspection add small runtime and debugging overhead.


## Caveats

- Annotations are looked up verbatim:
  a parameter annotated with, for example, `Annotated[Database, "primary"]` or a `NewType` is resolved only if the service is registered under exactly that type – not under the plain `Database`.

- Annotations are resolved when the returned factory is called for the first time.
  Forward references that are resolvable by then work fine, but types that only exist under {data}`typing.TYPE_CHECKING` can never be resolved and fail with a {class}`svcs.exceptions.ServiceNotFoundError`.

- Some objects (for example, HTTP client responses) are both awaitable *and* a context manager.
  {func}`svcs.aautowire` does not await such objects:
  they are treated as context managers and left to the container, which by default enters them and takes care of their cleanup.
  If you've registered the factory with *enter* set to `False`, you get the object as-is and have to enter – or await – it yourself.


## Autowiring a class

Best used as a wrapper during registration:

```python
from svcs import Container, Registry, autowire

class Service:
    def __init__(self, name: str) -> None:
        self.name = name

class Handler:
    def __init__(self, svc: Service, prefix: str = "svc:") -> None:
        self.svc = svc
        self.prefix = prefix

registry = Registry()
registry.register_value(Service, Service("api"))
registry.register_factory(Handler, autowire(Handler))

with Container(registry) as container:
    handler = container.get(Handler)
    print(handler.svc.name, handler.prefix)  # Output: "api svc:"
```


## Autowiring a function

Best used as a decorator on top of your factories:

```python
from svcs import Container, Registry, autowire

class Service:
    def __init__(self, name: str) -> None:
        self.name = name

@autowire
def build_label(svc: Service, suffix: int = 42) -> str:
    return f"{svc.name}{suffix}"

registry = Registry()
registry.register_value(Service, Service("api"))
registry.register_factory(str, build_label)

with Container(registry) as container:
    result = container.get(str)
    print(result)  # Output: "api42"
```


## API Reference

```{eval-rst}
.. autofunction:: svcs.autowire

.. autofunction:: svcs.aautowire
```
