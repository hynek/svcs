# Helpers

## What are Helpers?

Helpers are utilities and tools built on top of **svcs**.
They provide convenient shortcuts and patterns to speed up bootstrapping and common development tasks,
without altering the core functionality of the service locator.
They serve as higher-level abstractions that make working with `svcs` more ergonomic in specific use cases.

Helpers are optional.
You can choose to use them when they fit your needs,
or stick with the core `svcs` API for more explicit control.

## Autowiring

Autowiring is a technique that automatically resolves dependencies based on type annotations,
eliminating the need to manually specify each dependency when invoking a function or instantiating a class.
This reduces boilerplate and makes your code more declarative.

The autowiring helpers inject dependencies from a {class}`svcs.Container`
directly into function or class parameters based on their type annotations.
This is particularly useful when you want to build factories or handlers
that consume multiple services without explicitly passing them through each layer.
It handles positional and keyword only arguments as well as default values.
If a parameter cannot be resolved because the service has not been registered,
the default value is injected instead.

::: {note}
For asynchronous resolution, {meth}`svcs.aautowire` exists
and uses {meth}`svcs.Container.aget()` instead of {meth}`svcs.Container.get()`.
It supports both synchronous and asynchronous callables.
In async contexts or applications,
you should simply use {meth}`svcs.aautowire`.
:::

Pros:

- **Less Boilerplate:** Dependencies are resolved automatically from type annotations.
- **Clear Intent:** Signatures still document required services.
- **Async-Friendly:** `aautowire` works across sync and async callables.
- **Sensible Defaults:** Missing optional services fall back to parameter defaults.

Cons:

- **More Implicit:** Dependency lookup is less explicit than direct {meth}`svcs.Container.get()` calls.
- **Annotation-Driven:** Incorrect or missing type hints break resolution.
- **Extra Indirection:** Wrapping and introspection add small runtime and debugging overhead.


### Autowiring a function

Best used as a decorator on top of your factories.

```python
from svcs import Container, Registry
from svcs.helpers import autowire

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

### Autowiring a class

Best used as a wrapper during registration (Do not decorate the class itself!).

```python
from svcs import Container, Registry
from svcs.helpers import autowire

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
