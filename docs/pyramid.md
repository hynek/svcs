# Pyramid

*svcs*'s Pyramid integration uses Pyramid's {class}`pyramid.registry.Registry` to store its own `svcs.Registry` (yes, unfortunate name clash) and a [Tween] that attaches a fresh `svcs.Container` to every request.

---

The most important integration API for Pyramid is `svcs.pyramid.init()` that takes an {class}`pyramid.config.Configurator` and optionally the positions where to put its [Tween] using the *tween_under* and *tween_over* arguments.

Now every {class}`pyramid.request.Request` object that is passed into views will have an `svcs` attribute that is a `svcs.Container` that is scoped to the request:

% skip: start

```python
def view(request):
    db = request.svcs.get(Database)
```

## Registration

You can use `svcs.pyramid.register_(factory|value)(config, ...)` that work like their `svcs.Registry` counterparts but take a {class}`pyramid.config.Configurator` as the first option (or any other object that has a `registry: dict` field, really).

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

## Cleanup

You can use `svcs.pyramid.close_registry(config)` to close the registry that is attached to the {class}`pyramid.registry.Registry` of *config*.


## Thread Locals

::: {danger}
These functions only work from within an **active** Pyramid request.
:::

Despite being [discouraged], you can use Pyramid's thread locals to access the active container, or even services

So this:

```python
def view(request):
    container = svcs.pyramid.get_container()
    service1 = svcs.pyramid.get(Service)
    service2 = svcs.pyramid.get_abstract(AbstractService)
```

is equivalent to this:

```python
def view(request):
    container = request.svcs
    service1 = request.svcs.get(Service)
    service2 = request.svcs.get_abstract(AbstractService)
```

[Tween]: https://docs.pylonsproject.org/projects/pyramid/en/main/glossary.html#term-tween


## API Reference

### Application Life Cycle

```{eval-rst}
.. module:: svcs.pyramid

.. autofunction:: init
.. autofunction:: close_registry

.. autofunction:: get_container
.. autofunction:: get_registry

.. autoclass:: RegistryHaver()
```


### Registering Services

```{eval-rst}
.. autofunction:: register_factory
.. autofunction:: register_value
```


### Service Acquisition

Generally, you should use the `request.svcs` to access services.
But Pyramid _does_ also support to find the request and the registry using thread locals, so here's helper methods for that.
It's [discouraged] by the Pyramid developers, though.

```{eval-rst}
.. function:: get(svc_types)

   Same as :meth:`svcs.Container.get()`, but uses thread locals to find the
   current request.

.. autofunction:: get_abstract
```

[discouraged]: https://docs.pylonsproject.org/projects/pyramid/en/main/narr/threadlocals.html
