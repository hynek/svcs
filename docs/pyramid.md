# Pyramid

The most important integration API for Pyramid is `svcs.pyramid.init()` that takes an {class}`pyramid.config.Configurator` and optionally the positions where to put its [Tween](https://docs.pylonsproject.org/projects/pyramid/en/main/glossary.html#term-tween) using the *tween_under* and *tween_over* arguments.

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

    config = Configurator(settings=settings)

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

Despite being [discouraged](https://docs.pylonsproject.org/projects/pyramid/en/main/narr/threadlocals.html), you can use Pyramid's thread locals to access the active container, or even services:

```python
def view(request):
    container = svcs.pyramid.get_container()
    service1 = svcs.pyramid.get(Service)
    service2 = svcs.pyramid.get_abstract(AbstractService)
```
