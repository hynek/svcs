# Core Concepts

To understand how *svcs* works regardless of your environment, you must understand only two concepts: **registries** and **containers**.
They have different life cycles and different responsibilities.

In practice, you will use one of our [framework integrations](integrations/index.md) (or [write your own](integrations/custom.md)) and not the low-level API directly – but knowing what's happening underneath is good to dispel any concerns about magic.


## Registries

A **{class}`svcs.Registry`** allows registering factories for types.
A registry should live as long as your application lives and there should be only one per application.
Its only job is to store and retrieve factories along with some metadata.

It is possible to register either factory callables or values:

```python
>>> import svcs
>>> import uuid

>>> registry = svcs.Registry()

>>> registry.register_factory(uuid.UUID, uuid.uuid4)
>>> registry.register_value(str, "Hello World")
>>> uuid.UUID in registry
True
>>> str in registry
True
>>> int in registry
False
```

The values and return values of the factories don't have to be actual instances of the type they're registered for.
But the types must be *hashable* because they're used as keys in a lookup dictionary.


### Multiple Factories for the Same Type

Sometimes, it makes sense to have multiple instances of the same type.
For example, you might have multiple HTTP client pools or more than one database connection.

You can achieve this by using either {any}`typing.Annotated` (Python 3.9+, or in [*typing-extensions*](https://pypi.org/project/typing-extensions/)) or by using {keyword}`type` (Python 3.12+, use {any}`typing.NewType` on older versions).
You can also mix and match the two.
For instance, if you need a primary and a secondary database connection:

% invisible-code-block: python
%
% primary_url = "sqlite:///:memory:"
% secondary_url = "sqlite:///:memory:"

```python
from typing import Annotated, NewType

from sqlalchemy import Connection, create_engine

# Create the two connection engines
primary_engine = create_engine(primary_url)
secondary_engine = create_engine(secondary_url)

# Create unique types for both with two different approaches
PrimaryConnection = Annotated[Connection, "primary"]
SecondaryConnection = NewType("SecondaryConnection", Connection)
# Or on Python 3.12:
# type SecondaryConnection = Connection

# Register the factories to the aliases
registry.register_factory(PrimaryConnection, primary_engine.connect)
registry.register_factory(SecondaryConnection, secondary_engine.connect)
```

The type and content of the annotated metadata ("primary") are not important to *svcs*, as long as the whole type is hashable.


### Cleanup

It's possible to register a callback that is called when the *registry* is closed:

% invisible-code-block: python
%
% url = "sqlite:///:memory:"

```python
engine = create_engine(url)

registry.register_factory(
    Connection, engine.connect, on_registry_close=engine.dispose
)
```

If this callback fails, it's logged at warning level but otherwise ignored.
For instance, you could free a database connection pool in an {mod}`atexit` handler or *pytest* fixture.
This liberates you from keeping track of registered services yourself.
You can also use a registry as an (async) context manager that (a)closes automatically on exit.

*svcs* will raise a {class}`ResourceWarning` if a registry with pending cleanups is garbage-collected.


## Containers

A **{class}`svcs.Container`** uses a {class}`svcs.Registry` to lookup registered types and uses that information to create instances and to take care of their life cycles when you call its {meth}`~svcs.Container.get` or {meth}`~svcs.Container.aget` method:

```python
>>> container = svcs.Container(registry)

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

A container lives as long as you want the instances within to live -- for example, as long as a request lives.

Our {doc}`integrations/index` offer a `svcs_from()` function to extract the container from the current environment, and a `get()` (and/or `aget()`) function that transparently gets the service from the current container for you.
Depending on your web framework, you may have to pass the current request object as the first argument to `svcs_from()` / `get()` / `aget()`.

---

If a factory takes a first argument called `svcs_container` or the first argument (of any name) is annotated as being {class}`svcs.Container`, the current container instance is passed into the factory as the first *positional* argument allowing for recursive service acquisition:

```python
>>> container = svcs.Container(registry)

# Let's make the UUID predictable for our test!
>>> registry.register_value(uuid.UUID, uuid.UUID('639c0a5c-8d93-4a67-8341-fe43367308a5'))

>>> def factory(svcs_container) -> str:
...     return svcs_container.get(uuid.UUID).hex  # get the UUID, then work on it

>>> registry.register_factory(str, factory)

>>> container.get(str)
'639c0a5c8d934a678341fe43367308a5'
```

::: {note}
It is possible to overwrite registered service factories later -- for example, for testing -- **without monkey-patching**.
This is especially interesting if you want to replace a low-level service with a mock without re-jiggering all services that depend on it.

If there's a chance that the container has been used by your fixtures to acquire a service, it's possible that the service is already cached by the container.
In this case make sure to reset it by calling {meth}`svcs.Container.close` on it after overwriting.
Closing a container is idempotent and it's safe to use it again afterwards.

If your integration has a function called `overwrite_(value|factory)()`, it will do all of that for you.
Of course, you can also use {ref}`local-registries`.
:::


### Cleanup

If a factory returns a [context manager](https://docs.python.org/3/library/stdtypes.html#context-manager-types), it will be immediately entered and the instance will be added to the cleanup list (you can disable this behavior by passing `enter=False` to {meth}`~svcs.Registry.register_factory` and it's **off by default** for {meth}`~svcs.Registry.register_value`).
If a factory is a [generator](https://docs.python.org/3/tutorial/classes.html#generators) that *yields* the instance instead of returning it, it will be wrapped in a context manager automatically.
At the end, you run {meth}`svcs.Container.close()` and all context managers will be exited.
You can use this to close files, return database connections to a pool, and so on.

Async context managers and async generators work the same way.

You can also use containers as (async) context managers that (a)close automatically on exit:

```python
>>> reg = svcs.Registry()
>>> def clean_factory() -> str:
...     yield "Hello World"
...     print("Cleaned up!")
>>> reg.register_factory(str, clean_factory)
>>> with svcs.Container(reg) as con:
...     _ = con.get(str)
Cleaned up!
```

Failing cleanups are logged at warning level but otherwise ignored.

::: {important}
The key idea is that your business code doesn't have to care about cleaning up services it has acquired.
:::

That makes testing even easier because the business code makes fewer assumptions about the object it's getting.

*svcs* will raise a {class}`ResourceWarning` if a container with pending cleanups is garbage-collected.

(local-registries)=

### Container-Local Registries

::: {versionadded} 23.21.0
:::

Sometimes, you want to register a factory or value that's only valid within a container.
For example, you might want to register a factory that depends on data from a request object.
Per-request factories, if you will.

This is where container-local registries come in.
They are created implicitly by calling {meth}`svcs.Container.register_local_factory()` and {meth}`svcs.Container.register_local_value()`.
When looking up factories in a container, the local registry takes precedence over the global one, and it is closed along with the container:

```python
>>> container = svcs.Container(registry)
>>> registry.register_value(str, "Hello World!")
>>> container.register_local_value(str, "Goodbye Cruel World!")
>>> container.get(str)
'Goodbye Cruel World!'
>>> container.close()  # closes both container & its local registry
>>> registry.close()   # closes the global registry
```

::: {warning}
Nothing is going to stop you from letting your global factories depend on local ones -- similarly to template subclassing.

For example, you could define your database connection like this:

```python
from sqlalchemy import text

def connect_and_set_user(svcs_container):
    user_id = svcs_container.get(User).user_id
    with engine.connect() as conn:
        conn.execute(text("SET user = :id", {"id": user_id}))

        yield conn

registry.register_factory(Connection, connect_and_set_user)
```

And then, somewhere in a middleware, define a local factory for the `Request` type using something like:

```python
def middleware(request):
    container.register_local_value(User, User(request.user_id, ...))
```

**However**, then you have to be very careful around the caching of created services.
If your application requests a `Connection` instance before you register the local `Request` factory, the `Connection` factory will either crash or be created with the wrong user (for example, if you defined a stub/fallback user in the global registry).

It is safer and easier to reason about your code if you keep the dependency arrows point from the local registry to the global one:

% skip: next -- Python 3.12

```python
# The global connection factory that creates and cleans up vanilla
# connections.
registry.register_factory(Connection, engine.connect)

# Create a type alias with an idiomatic name.
type ConnectionWithUserID = Connection

def middleware(request):
    def set_user_id(svcs_container):
        conn = svcs_container.get(Connection)
        conn.execute(text("SET user = :id", {"id": user_id}))

        return conn

    # Use a factory to keep the service lazy. If the view never asks for a
    # connection, we never connect -- or set a user.
    container.register_local_factory(ConnectionWithUserID, set_user_id)
```

Now the type name expresses the purpose of the object and it doesn't matter if there's already a non-user-aware `Connection` in the global registry.
:::


(health)=

### Health Checks

Each registered service may have a `ping` callable that you can use for health checks.
You can request all pingable registered services with {meth}`svcs.Container.get_pings()`.
This returns a list of {class}`svcs.ServicePing` objects that currently have a name property to identify the ping and a {meth}`~svcs.ServicePing.ping()` method that instantiates the service, adds it to the cleanup list, and runs the ping.

If you have async services (factory or ping callable), you can use {meth}`~svcs.ServicePing.aping()` instead.
`aping()` works with sync services, too, so you can use it universally in async code.
You can look at the {attr}`~svcs.ServicePing.is_async` property to check whether you *need* to use `aping()`, though.

Here's how a health check endpoint could look like:

<!-- begin health checks -->
:::: {tab-set}

::: {tab-item} AIOHTTP
```{literalinclude} examples/aiohttp/health_check.py
```
:::
::: {tab-item} FastAPI
```{literalinclude} examples/fastapi/health_check.py
```
:::
::: {tab-item} Flask
```{literalinclude} examples/flask/health_check.py
```
:::
::: {tab-item} Pyramid
```{literalinclude} examples/pyramid/health_check.py
```
:::
::: {tab-item} Starlette
```{literalinclude} examples/starlette/health_check.py
```
:::

::::
<!-- end health checks -->

Now, you can point your monitoring tool of choice -- like Prometheus's [Blackbox Exporter](https://github.com/prometheus/blackbox_exporter) or [Nagios](https://www.nagios.org) -- at it and you'll get alerted whenever the application is broken.


## Life Cycle Summary

While *svcs*'s core is entirely agnostic on how you use the registry and the container, all our {doc}`integrations/index` follow the same life cycle:

- The {class}`svcs.Registry` objects live on **application-scoped** objects like {attr}`flask.Flask.config`.
- The {class}`svcs.Container` objects live on **request-scoped** objects like {data}`flask.g`.

You're free to structure your own integrations as you want, though.


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
   :members: get, aget, get_abstract, aget_abstract, register_local_factory, register_local_value, close, aclose, get_pings, __contains__

.. autoclass:: ServicePing()
   :members: name, ping, aping, is_async

.. autoclass:: svcs.exceptions.ServiceNotFoundError
```
