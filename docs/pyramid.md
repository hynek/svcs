# Pyramid

*svcs*'s Pyramid integration uses Pyramid's {class}`pyramid.registry.Registry` to store its own {class}`svcs.Registry` (yes, unfortunate name clash) and a {term}`tween` that attaches a fresh {class}`svcs.Container` to every request and closes it afterwards.


## Initialization

The most important integration API for Pyramid is {func}`svcs.pyramid.init()` that takes an {class}`pyramid.config.Configurator` and optionally the positions where to put its {term}`tween` using the *tween_under* and *tween_over* arguments.

You can use {func}`svcs.pyramid.register_factory()` and {func}`svcs.pyramid.register_value()` that work like their {class}`svcs.Registry` counterparts but take a {class}`pyramid.config.Configurator` as the first option (or any other object that has a `registry: dict` field, really).

So you application factory is going to look something like this:

```python
def make_app():
    ...

    with Configurator(settings=settings) as config:
        svcs.pyramid.init(config)
        svcs.pyramid.register_factory(config, Database, db_factory)

        ...

        return config.make_wsgi_app()
```


## Service Acquisition

Every {class}`~pyramid.request.Request` object that is passed into views will have an `svcs` attribute that is a {class}`svcs.Container` that is scoped to the request.
You can use {func}`svcs.pyramid.services()` to access it in a type-safe way:


```python
from svcs.pyramid import services

def view(request):
    db = services(request).get(Database)
```

If you don't care about type checking, you can use `request.svcs` directly.


## Cleanup

You can use {func}`svcs.pyramid.close_registry()` to close the registry that is attached to the {class}`pyramid.registry.Registry` of the config or app object that you pass as the only parameter.


## Thread Locals

::: {danger}
These functions only work from within an **active** Pyramid request.
:::

Despite being [discouraged](<inv:#narr/threadlocals>), you can use Pyramid's thread locals to access the active container, or even services

So this:

```python
def view(request):
    container = svcs.pyramid.services()
    service1 = svcs.pyramid.get(Service)
    service2 = svcs.pyramid.get_abstract(AbstractService)
```

is equivalent to this:

```python
def view(request):
    container = services(request)
    service1 = container.get(Service)
    service2 = container.get_abstract(AbstractService)
```


## API Reference

### Application Life Cycle

```{eval-rst}
.. module:: svcs.pyramid

.. autofunction:: init
.. autofunction:: close_registry

.. autofunction:: services
.. autofunction:: get_registry

.. autoclass:: PyramidRegistryHaver()
```


### Registering Services

```{eval-rst}
.. autofunction:: register_factory
.. autofunction:: register_value
```


### Service Acquisition

You should use `services(request).get()` to access services.
But Pyramid _does_ also support to find the request and the registry using thread locals, so here's helper methods for that.
It's [discouraged](<inv:#narr/threadlocals>) by the Pyramid developers, though.

```{eval-rst}
.. function:: get(svc_types)

   Same as :meth:`svcs.Container.get()`, but uses thread locals to find the
   current request.

.. autofunction:: get_abstract
```
