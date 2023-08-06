# Core Concepts

You will probably use some framework integration and not the low-level API directly, but knowing what's happening underneath is good to dispel any concerns about magic.

*svcs* has two core concepts: **registries** and **containers** that have different life cycles and responsibilities.


## Registries

A **`svcs.Registry`** allows to register factories for types.
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
This frees you from keeping track of registered resources yourself.
You can also use `Registry` as an (async) context manager that (a)closes automatically on exit.


## Containers

A **`svcs.Container`** uses a `svcs.Registry` to lookup registered types and uses that information to create instances and to take care of their life cycles:

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

If a factory takes a first argument called `svcs_container` or the first argument (of any name) is annotated as being `svcs.Container`, the current container instance is passed into the factory as the first *positional* argument allowing for recursive service acquisition:

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

You have to remove possibly cached instances from the container though (`Container.forget_about()`).
The Flask integration takes care of this for you.

How to achieve this in other frameworks elegantly is TBD.
:::


### Cleanup

If a factory is a [generator](https://docs.python.org/3/tutorial/classes.html#generators) and *yields* the instance instead of returning it, the generator will be remembered by the container.
At the end, you run `container.close()` and all generators will be finished (i.e. called `next(factory)` again).
You can use this to close files, return database connections to a pool, et cetera.

If you have async generators, use `await container.aclose()` instead which calls `await anext(factory)` on all async generators (and `next(factory)` on sync ones).
You can also use `Registry` as an (async) context manager that (a)closes automatically on exit.

Failing cleanups are logged at `warning` level but otherwise ignored.

**The key idea is that your business code doesn't have to care about cleaning up resources it has requested.**

That makes it even easier to test it because the business codes makes fewer assumptions about the object it's getting.


### Health Checks

Each registered service may have a `ping` callable that you can use for health checks.
You can request all pingable registered services with `container.get_pings()`.
This returns a list of `ServicePing` objects that currently have a name property to identify the ping and a `ping` method that instantiates the service, adds it to the cleanup list, and runs the ping.
If you have async resources (either factory or ping callable), you can use `aping()` instead.
`aping()` works with sync resources too, so you can use it universally in async code.
You can look at the `is_async` property to check whether you *need* to use `aget()`, though.


## Summary

The `svc.Registry` object should live on an application-scoped object like Flask's `app.config` object.
On the other hand, the `svc.Container` object should live on a request-scoped object like Flask's `g` object or Pyramid's `request` object.


::: {important}
The core APIs only use vanilla objects without any global state but also without any comfort.
It gets more interesting when using framework-specific integrations where the life cycle of the container and, thus, services is handled automatically.
:::
