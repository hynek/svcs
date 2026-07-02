# Autowiring

::: {versionadded} 26.1.0
:::

Autowiring is an optional technique that automatically resolves dependencies based on type annotations, eliminating the need to manually specify each dependency when invoking a function or instantiating a class.
This reduces boilerplate and makes your code more declarative.

The autowiring functions inject dependencies from a {class}`svcs.Container`
directly into function or class parameters based on their type annotations.
This is particularly useful when you want to build factories or handlers
that consume multiple services without explicitly passing them through each layer:

```python
>>> from dataclasses import dataclass

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

>>> # Before: wire the dependencies by hand.
>>> registry.register_factory(
...     AppServices,
...     lambda svcs_container: AppServices(
...         db=svcs_container.get(Database),
...         cache=svcs_container.get(Cache),
...     ),
... )

>>> # After: the type annotations are enough.
>>> registry.register_factory(AppServices, svcs.autowire(AppServices))

>>> with svcs.Container(registry) as container:
...     container.get(AppServices)
AppServices(db=Database(), cache=Cache())
```

It handles regular, positional-only, and keyword-only parameters, and ignores variadic ones (`*args` and `**kwargs`).
If a parameter cannot be resolved because the service has not been registered,
the default value is injected instead.

::: {note}
For asynchronous resolution, {func}`svcs.aautowire` exists
and uses {meth}`svcs.Container.aget()` instead of {meth}`svcs.Container.get()`.
It supports both synchronous and asynchronous callables, therefore in async contexts you can always use {func}`svcs.aautowire`.
:::

Pros:

- **Less Boilerplate:** Dependencies are resolved automatically from type annotations.
- **Clear Intent:** Signatures still document required services.
- **Sensible Defaults:** Missing optional services fall back to parameter defaults.

Cons:

- **More Implicit:** Dependency lookup is less explicit than direct {meth}`svcs.Container.get()` calls.
- **Annotation-Driven:** Incorrect or missing type hints break resolution.
- **Extra Indirection:** Wrapping and introspection add small runtime and debugging overhead.


## Autowiring a function

Best used as a decorator on top of your factories.

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

::: {warning}
Do **not** decorate the class itself!
Decorating the class replaces the class with the autowire factory, so its name suddenly refers to a function, not a type.

Wrap the class only at register time.
:::


## API Reference

```{eval-rst}
.. autofunction:: svcs.autowire

.. autofunction:: svcs.aautowire
```
