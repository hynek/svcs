# Core Concepts

You will probably use some framework integration and not the low-level API directly, but knowing what's happening underneath is good to dispel any concerns about magic.

*svcs* has two core concepts: **registries** and **containers** that have different life cycles and responsibilities.


## Registries

A **{class}`svcs.Registry`** allows to register factories for types.
It's expected to live as long as your application lives.
Its only job is to store and retrieve factories along with some metadata.

It is possible to register either factory callables or values:

```python
>>> import svcs
>>> import uuid

>>> reg = svcs.Registry()

>>> reg.register_factory(uuid.UUID, uuid.uuid4)
>>> reg.register_value(str, "Hello World")
>>> uuid.UUID in reg
True
>>> str in reg
True
>>> int in reg
False
```

The values and return values of the factories don't have to be actual instances of the type they're registered for.
But the types must be *hashable* because they're used as keys in a lookup dictionary.


### Cleanup

It's possible to register a callback that is called when the *registry* is closed:

% skip: next

```python
registry.register_factory(
    Connection, connection_factory, on_registry_close=engine.dispose
)
```

If this callback fails, it's logged at warning level but otherwise ignored.
For instance, you could free a database connection pool in an {mod}`atexit` handler or *pytest* fixture.
This frees you from keeping track of registered services yourself.
You can also use a registry as an (async) context manager that (a)closes automatically on exit.


## Containers

A **{class}`svcs.Container`** uses a {class}`svcs.Registry` to lookup registered types and uses that information to create instances and to take care of their life cycles:

```python
>>> container = svcs.Container(reg)

>>> uuid.UUID in container
False
>>> u = container.get(uuid.UUID)
>>> u
UUID('...')
>>> uuid.UUID in container
True
>>> # Calling get() again returns the SAME UUID instance!
>>> # Good for DB connections, bad for UUIDs.
>>> u is container.get(uuid.UUID)
True
>>> container.get(str)
'Hello World'
```

A container lives as long as you want the instances to live – for example, as long as a request lives.

If a factory takes a first argument called `svcs_container` or the first argument (of any name) is annotated as being {class}`svcs.Container`, the current container instance is passed into the factory as the first *positional* argument allowing for recursive service acquisition:

```python
>>> container = svcs.Container(reg)

# Let's make the UUID predictable for our test!
>>> reg.register_value(uuid.UUID, uuid.UUID('639c0a5c-8d93-4a67-8341-fe43367308a5'))

>>> def factory(svcs_container) -> str:
...     return svcs_container.get(uuid.UUID).hex  # get the UUID, then work on it

>>> reg.register_factory(str, factory)

>>> container.get(str)
'639c0a5c8d934a678341fe43367308a5'
```

::: {note}
It is possible to overwrite registered service factories later – e.g., for testing – **without monkey-patching**.
This is especially interesting if you want to replace a low-level service with a mock without re-jiggering all services that depend on it.

You have to remove possibly cached instances from the container though ({meth}`svcs.Container.forget_about()`).
The Flask integration takes care of this for you.

How to achieve this in other frameworks elegantly is TBD.
:::


### Cleanup

If a factory is a [generator](https://docs.python.org/3/tutorial/classes.html#generators) and *yields* the instance instead of returning it, the generator will be remembered by the container.
At the end, you run {meth}`svcs.Container.close()` and all generators will be finished (i.e. called `next(factory)` again).
You can use this to close files, return database connections to a pool, et cetera.

If you have async generators, await {meth}`svcs.Container.aclose()` instead which calls `await anext(factory)` on all async generators (and `next(factory)` on sync ones).
You can also use containers as (async) context managers that (a)close automatically on exit:

```python
>>> reg = svcs.Registry()
>>> def factory() -> str:
...     yield "Hello World"
...     print("Cleaned up!")
>>> reg.register_factory(str, factory)

>>> with svcs.Container(reg) as con:
...     _ = con.get(str)
Cleaned up!
```

Failing cleanups are logged at `warning` level but otherwise ignored.

::: {important}
The key idea is that your business code doesn't have to care about cleaning up services it has requested.
:::

That makes it even easier to test because the business codes makes fewer assumptions about the object it's getting.

(health)=

### Health Checks

Each registered service may have a `ping` callable that you can use for health checks.
You can request all pingable registered services with {meth}`svcs.Container.get_pings()`.
This returns a list of {class}`svcs.ServicePing` objects that currently have a name property to identify the ping and a `ping` method that instantiates the service, adds it to the cleanup list, and runs the ping.

If you have async services (either factory or ping callable), you can use `aping()` instead.
`aping()` works with sync services too, so you can use it universally in async code.
You can look at the `is_async` property to check whether you *need* to use `aget()`, though.

Here's an example for a health check endpoint in Pyramid[^flask]:

[^flask]: See the [Flask integration](flask.md) chapter for a Flask equivalent.

```{literalinclude} examples/health_check_pyramid.py
```


## Summary

The {class}`svcs.Registry` object should live on an application-scoped object like Flask's {attr}`flask.Flask.config` object or in Pyramid's {attr}`pyramid.config.Configurator.registry`.
On the other hand, the {class}`svcs.Container` object should live on a request-scoped object like Flask's {data}`~flask.g` object or Pyramid's {class}`~pyramid.request.Request` object.


::: {important}
The core APIs only use vanilla objects without any global state but also without any comfort.
It gets more interesting when using framework-specific integrations where the life cycle of the container and, thus, services is handled automatically.
:::


## API Reference

```{eval-rst}
.. module:: svcs

.. autoclass:: Registry()
   :members: register_factory, register_value, close, aclose, __contains__

.. autoclass:: Container()
   :members: get, aget, get_abstract, aget_abstract, close, aclose, forget_about, get_pings, __contains__

.. autoclass:: ServicePing()
   :members: name, ping, aping, is_async
```
