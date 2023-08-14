# Core Concepts

You will probably use some framework integration and not the low-level API directly, but knowing what's happening underneath is good to dispel any concerns about magic.

*svcs* has two core concepts: **registries** and **containers** that have different life cycles and responsibilities.


## Registries

A **{class}`svcs.Registry`** allows registering factories for types.
A registry should live as long as your application lives and there should be only one per application.
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
This liberates you from keeping track of registered services yourself.
You can also use a registry as an (async) context manager that (a)closes automatically on exit.

*svcs* will raise a {class}`ResourceWarning` if a registry with pending cleanups is garbage-collected.


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

A container lives as long as you want the instances to live -- for example, as long as a request lives.

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
It is possible to overwrite registered service factories later -- e.g., for testing -- **without monkey-patching**.
This is especially interesting if you want to replace a low-level service with a mock without re-jiggering all services that depend on it.

If there's a chance that the container has been used by your fixtures to acquire a service, it's possible that the service is already cached by the container.
In this case make sure to reset it by calling {meth}`svcs.Container.close` on it after overwriting.
Closing a container is idempotent and it's safe to use it again afterwards.

If your integration has a function called `overwrite_(value|factory)()`, it will do all of that for you.
:::


### Cleanup

If a factory returns a [context manager](https://docs.python.org/3/library/stdtypes.html#context-manager-types), it will be immediately entered and the instance will be added to the cleanup list (you can disabled this behavior by passing `enter=False` to {meth}`~svcs.Registry.register_factory` and {meth}`~svcs.Registry.register_value`).
If a factory is a [generator](https://docs.python.org/3/tutorial/classes.html#generators) that *yields* the instance instead of returning it, it will be wrapped in a context manager automatically.
At the end, you run {meth}`svcs.Container.close()` and all context managers will be exited.
You can use this to close files, return database connections to a pool, et cetera.

Async context managers and async generators work the same way.

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

Failing cleanups are logged at warning level but otherwise ignored.

::: {important}
The key idea is that your business code doesn't have to care about cleaning up services it has requested.
:::

That makes testing even easier because the business code makes fewer assumptions about the object it's getting.

*svcs* will raise a {class}`ResourceWarning` if a container with pending cleanups is garbage-collected.

(health)=

### Health Checks

Each registered service may have a `ping` callable that you can use for health checks.
You can request all pingable registered services with {meth}`svcs.Container.get_pings()`.
This returns a list of {class}`svcs.ServicePing` objects that currently have a name property to identify the ping and a {meth}`~svcs.ServicePing.ping()` method that instantiates the service, adds it to the cleanup list, and runs the ping.

If you have async services (factory or ping callable), you can use {meth}`~svcs.ServicePing.aping()` instead.
`aping()` works with sync services, too, so you can use it universally in async code.
You can look at the {attr}`~svcs.ServicePing.is_async` property to check whether you *need* to use `aping()`, though.

Here's how a health check endpoint could look like:

::: {tab} AIOHTTP
```{literalinclude} examples/aiohttp/health_check.py
```
:::
::: {tab} Flask
```{literalinclude} examples/flask/health_check.py
```
:::
::: {tab} Pyramid
```{literalinclude} examples/flask/health_check.py
```
:::

## Life Cycle Summary

- The {class}`svcs.Registry` object should live on an **application-scoped** object like Flask's {attr}`flask.Flask.config` object.
- The {class}`svcs.Container` object should live on a **request-scoped** object like Flask's {data}`~flask.g` object.


::: {important}
The core APIs only use vanilla objects without any global state -- but also without any comfort.

It gets more interesting when using framework-specific integrations where the life cycle of the container and, thus, services is handled automatically.
:::


## Debugging Registrations

If you are confused about where a particular factory for a type has been defined, *svcs* logs every registration at debug level along with a stack trace.

Set the *svcs* logger to `DEBUG` to see them:

```{literalinclude} examples/debugging_with_logging.py
```

It gives you an output like this:

```text
svcs: registered factory <built-in method now of type object at 0x103468980> for service type datetime.datetime
Stack (most recent call last):
  File "/Users/hynek/FOSS/svcs/docs/examples/debugging_with_logging.py", line 41, in <module>
    reg.register_factory(datetime, datetime.now)
  File "/Users/hynek/FOSS/svcs/src/svcs/_core.py", line 216, in register_factory
    log.debug(
svcs: registered value 'Hello World' for service type builtins.str
Stack (most recent call last):
  File "/Users/hynek/FOSS/svcs/docs/examples/debugging_with_logging.py", line 42, in <module>
    reg.register_value(str, "Hello World")
  File "/Users/hynek/FOSS/svcs/src/svcs/_core.py", line 252, in register_value
    log.debug(
```

You can see that the datetime factory and the str value have both been registered in `debugging_with_logging.py`, down to the line number.


## API Reference

```{eval-rst}
.. module:: svcs

.. autoclass:: Registry()
   :members: register_factory, register_value, close, aclose, __contains__

.. autoclass:: Container()
   :members: get, aget, get_abstract, aget_abstract, close, aclose, get_pings, __contains__

.. autoclass:: ServicePing()
   :members: name, ping, aping, is_async
```
