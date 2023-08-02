<!-- begin-logo -->
<p align="center">
  <a href="https://github.com/hynek/svcs/">
    <img src="docs/_static/logo_with_name.svg" width="25%" alt="svcs logo showing a radar" />
  </a>
</p>

<p align="center">
  A Lightweight Service Locator for Python.
</p>

<!-- end-logo -->

<p align="center">
  <img alt="PyPI - Status" src="https://img.shields.io/pypi/status/svcs">
  <a href="./LICENSE">
    <img alt="PyPI - License" src="https://img.shields.io/pypi/l/svcs">
  </a>
  <a href="https://pypi.org/project/svcs/">
    <img alt="PyPI" src="https://img.shields.io/pypi/v/svcs">
  </a>
  <a href="https://pypi.org/project/svcs/">
    <img alt="PyPI - Supported Python versions" src="https://img.shields.io/pypi/pyversions/svcs.svg">
  </a>
</p>

---

<!-- begin-pypi -->

> [!WARNING] ☠️ Not ready yet! ☠️
>
> This project is only public to [gather feedback](https://github.com/hynek/svcs/discussions), and everything can and will change until the project is proclaimed stable.
>
> Currently only [**Flask** support](#flask) is production-ready, but API details can still change.
>
> At this point, it's unclear whether this project will become a "proper Hynek project".
> I will keep using it for my work projects, but whether this will grow beyond my personal needs depends on community interest.

*svcs* (pronounced *services*) is a [service locator](https://en.wikipedia.org/wiki/Service_locator_pattern) for Python.
It provides you with a central place to register factories for types/interfaces and then imperatively request instances of those types with **automatic cleanup** and **health checks**.

---

**This allows you to configure and manage all your resources in *one central place* and access them in a *consistent* way without worrying about *cleaning them up*.**

---

In practice that means that at runtime, you say "*Give me a database connection*!", and *svcs* will give you whatever you've configured it to return when asked for a database connection.
This can be an actual database connection or it can be a mock object for testing.
All of this happens *within* your application – service locators are **not** related to service discovery.

If you follow the [*Dependency Inversion Principle*](https://en.wikipedia.org/wiki/Dependency_inversion_principle) (aka "*program against interfaces, not implementations*"), you would register concrete factories for abstract interfaces; in Python usually a [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol) or an [*abstract base class*](https://docs.python.org/3.11/library/abc.html).

Benefits:

- Eliminates tons of repetitive **boilerplate** code,
- unifies **acquisition** and **cleanups** of resources,
- simplifies **testing**,
- and allows for easy **health checks** across *all* resources.

The goal is to minimize your business code to:

```python
def view(request):
    db = request.services.get(Database)
    api = request.services.get(WebAPIClient)
```

or, if you don't shy away from some global state, even:

```python
def view():
    db = services.get(Database)
    api = services.get(WebAPIClient)
```

The latter already works with [Flask](#flask) by utilizing the [`g` object](https://flask.palletsprojects.com/en/latest/api/#flask.g).

You set it up like this:

<!--
; skip: next
-->

```python
import atexit

from sqlalchemy import Connection, create_engine

...

engine = create_engine("postgresql://localhost")

def connection_factory():
    with engine.connect() as conn:
        yield conn

registry = svcs.Registry()
registry.register_factory(
    Connection,
    connection_factory,
    on_registry_close=engine.dispose
)

@atexit.register
def cleanup():
    registry.close()  # calls engine.dispose()
```

The generator-based setup and cleanup may remind you of [*pytest* fixtures](https://docs.pytest.org/en/stable/explanation/fixtures.html).
The hooks that are defined as `on_registry_close` are called when you call `Registry.close()` – e.g. when your application is shutting down.

*svcs* comes with **full async** support via a-prefixed methods (i.e. `aget()` instead of `get()`, et cetera).

> [!IMPORTANT]
> All of this may look over-engineered if you have only one or two resources.
> However, it starts paying dividends *very fast* once you go past that.


## Is this Dependency Injection!?

No.

Although the concepts are related and share the idea of having a central registry of services, the ways they provide those services are fundamentally different:
[Dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) always passes your dependencies as arguments while you actively ask a service locator for them when you need them.
That usually requires less opaque magic since nothing meddles with your function/method definitions.
But you can use, e.g., your web framework's injection capabilities to inject the locator object into your views and benefit from *svcs*'s upsides without giving up some of DI's ones.

The active acquisition of resources by calling `get()` when you *know* for sure you're going to need it avoids the conundrum of either having to pass a factory (e.g., a connection pool – which also puts the onus of cleanup on you) or eagerly creating resources that you never use:

<!--
; skip: next
-->
```python
def view(request):
    if request.form.valid():
        # Form is valid; only NOW get a DB connection
        # and pass it into your business logic.
        return handle_form_data(
            request.services.get(Database),
            form.data,
        )

    raise InvalidFormError()
```

The main downside is that it's impossible to verify whether all required dependencies have been configured without running the code.

If you still prefer dependency injection, check out [*incant*](https://github.com/Tinche/incant).

<!-- end-pypi -->


## Low-Level API

You will probably use some framework integration and not the low-level API directly, but knowing what's happening underneath is good to dispel any concerns about magic.

*svcs* has two core concepts: **registries** and **containers** that have different life cycles and responsibilities.


### Registries

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
```

The values and return values of the factories don't have to be actual instances of the type they're registered for.
But the types must be *hashable* because they're used as keys in a lookup dictionary.

It's possible to register a callback that is called when the *registry* is closed:

<!--
; skip: next
-->

```python
registry.register_factory(
    Connection, connection_factory, on_registry_close=engine.dispose
)
```

If this callback fails, it's logged at warning level but otherwise ignored.
For instance, you could free a database connection pool in an [`atexit` handler](https://docs.python.org/3/library/atexit.html).
This frees you from keeping track of registered resources yourself.


### Containers

A **`svcs.Container`** uses a `svcs.Registry` to lookup registered types and uses that information to create instances and to take care of their life cycles:

```python
>>> container = svcs.Container(reg)

>>> u = container.get(uuid.UUID)
>>> u
UUID('...')
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

> [!NOTE]
> It is possible to overwrite registered service factories later – e.g., for testing – **without monkey-patching**.
> This is especially interesting if you want to replace a low-level service with a mock without re-jiggering all services that depend on it.
>
> You have to remove possibly cached instances from the container though (`Container.forget_about()`).
> The Flask integration takes care of this for you.
>
> How to achieve this in other frameworks elegantly is TBD.


#### Cleanup

If a factory is a [generator](https://docs.python.org/3/tutorial/classes.html#generators) and *yields* the instance instead of returning it, the generator will be remembered by the container.
At the end, you run `container.close()` and all generators will be finished (i.e. called `next(factory)` again).
You can use this to close files, return database connections to a pool, et cetera.

If you have async generators, use `await container.aclose()` instead which calls `await anext(factory)` on all async generators (and `next(factory)` on sync ones).

Failing cleanups are logged at `warning` level but otherwise ignored.

**The key idea is that your business code doesn't have to care about cleaning up resources it has requested.**

That makes it even easier to test it because the business codes makes fewer assumptions about the object it's getting.


#### Health Checks

Each registered service may have a `ping` callable that you can use for health checks.
You can request all pingable registered services with `container.get_pings()`.
This returns a list of `ServicePing` objects that currently have a name property to identify the ping and a `ping` method that instantiates the service, adds it to the cleanup list, and runs the ping.
If you have async resources (either factory or ping callable), you can use `aping()` instead.
`aping()` works with sync resources too, so you can use it universally in async code.
You can look at the `is_async` property to check whether you *need* to use `aget()`, though.


### Summary

The `svc.Registry` object should live on an application-scoped object like Flask's `app.config` object.
On the other hand, the `svc.Container` object should live on a request-scoped object like Flask's `g` object or Pyramid's `request` object.


> [!NOTE]
> The core APIs only use vanilla objects without any global state but also without any comfort.
> It gets more interesting when using framework-specific integrations where the life cycle of the container and, thus, services is handled automatically.


## Flask

*svcs* has grown from my frustration with the repetitiveness of using the `get_x` that creates an `x` and then stores it on the `g` object [pattern](https://flask.palletsprojects.com/en/latest/appcontext/#storing-data).

Therefore it comes with Flask support out of the box in the form of the `svcs.flask` module.
It:

- puts the registry into `app.config["svcs_registry"]`,
- unifies the caching of services on the `g` object by putting a container into `g.svcs_container`,
- transparently retrieves them from there for you,
- and installs a [`teardown_appcontext()`](http://flask.pocoo.org/docs/latest/api#flask.Flask.teardown_appcontext) handler that calls `close()` on the container when a request is done.

---

You can add support for *svcs* by calling `svcs.flask.init_app(app)` in your [*application factory*](https://flask.palletsprojects.com/en/latest/patterns/appfactories/).
For instance, to create a factory that uses a SQLAlchemy engine to produce connections, you could do this:


<!--
; skip: start
-->

```python
import atexit

from flask import Flask
from sqlalchemy import Connection, create_engine
from sqlalchemy.sql import text

import svcs


def create_app(config_filename):
    app = Flask(__name__)

    ...

    ##########################################################################
    # Set up the registry using Flask integration.
    app = svcs.flask.init_app(app)

    # Now, register a factory that calls `engine.connect()` if you ask for a
    # `Connection`. Since we use yield inside of a context manager, the
    # connection gets cleaned up when the container is closed.
    # If you ask for a ping, it will run `SELECT 1` on a new connection and
    # clean up the connection behind itself.
    engine = create_engine("postgresql://localhost")
    def connection_factory():
        with engine.connect() as conn:
            yield conn

    ping = text("SELECT 1")
    svcs_flask.register_factory(
        # The app argument makes it good for custom init_app() functions.
        app,
        Connection,
        connection_factory,
        ping=lambda conn: conn.execute(ping),
        on_registry_close=engine.dispose,
    )

    # You also use svcs WITHIN factories:
    svcs_flask.register_factory(
        app, # <---
        AbstractRepository,
        # No cleanup, so we just return an object using a lambda
        lambda: Repository.from_connection(
            svcs.flask.get(Connection)
        ),
    )

    @atexit.register
    def cleanup() -> None:
        """
        Clean up all pools when the application shuts down.
        """
        log.info("app.cleanup.start")
        svcs.flask.close_registry(app)  # calls engine.dispose()
        log.info("app.cleanup.done")
    ##########################################################################

    ...

    return app
```

Now you can request the `Connection` object in your views:

```python
@app.get("/")
def index() -> flask.ResponseValue:
    conn: Connection = svcs.flask.get(Connection)
```

If you have a [health endpoint](https://kubernetes.io/docs/reference/using-api/health-checks/), it could look like this:

```python
@app.get("healthy")
def healthy() -> flask.ResponseValue:
    """
    Ping all external services.
    """
    ok: list[str] = []
    failing: list[dict[str, str]] = []
    code = 200

    for svc in svcs.flask.get_pings():
        try:
            svc.ping()
            ok.append(svc.name)
        except Exception as e:
            failing.append({svc.name: repr(e)})
            code = 500

    return {"ok": ok, "failing": failing}, code
```


### Testing

Having a central place for all your services, makes it obvious where to mock them for testing.
So, if you want the connection service to return a mock `Connection`, you can do this:

```python
from unittest.mock import Mock

def test_handles_db_failure():
    """
    If the database raises an exception, the endpoint should return a 500.
    """
    app = create_app("test.cfg")
    with app.app_context():
        conn = Mock(spec_set=Connection)
        conn.execute.side_effect = Exception("Database is down!")

        #################################################
        # Overwrite the Connection factory with the Mock.
        # This is all it takes to mock the database.
        reg_svc.flask.replace_value(Connection, conn)
        #################################################

        # Now, the endpoint should return a 500.
        response = app.test_client().get("/")
        assert response.status_code == 500
```

> [!IMPORTANT]
> The `replace_(factory|value)` method *requires* an application context and ensures that if a factory/value has already been created *and cached*, they're removed before the new factory/value is registered.
>
> Possible situations where this can occur are *pytest* fixtures where you don't control the order in which they're called.


### Quality of Life

In practice, you can simplify/beautify the code within your views by creating a `services` module that re-exports those Flask helpers.

Say this is `app/services.py`:

```python
from svcs.flask import (
    get,
    get_pings,
    init_app,
    register_factory,
    register_value,
    replace_factory,
    replace_value,
)


__all__ = [
    "get_pings",
    "get",
    "init_app",
    "register_factory",
    "register_value",
    "replace_factory",
    "replace_value",
]
```

Now you can register services in your application factory like this:

```python
from your_app import services

def init_app(app):
    app = services.init_app(app)
    services.register_factory(app, Connection, ...)
    return app
```

And you get them in your views like this:

```python
from your_app import services

@app.route("/")
def index():
    conn: Connection = services.get(Connection)
```

🧑‍🍳💋


## Caveats

One would expect the the `Container.get()` method would have a type signature like `get(type: type[T]) -> T`.
Unfortunately, that's currently impossible because it [precludes the usage of `Protocols` and *abstract base classes* as service types](https://github.com/python/mypy/issues/4717), making this package pointless.

Therefore it returns `Any`, and until Mypy changes its stance, you have to use it like this:

```python
conn: Connection = container.get(Connection)
```

If types are more important to you than a unified interface, you can always wrap it:

```python
def get_connection() -> Connection:
    return svcs.flask.get(Connection)
```

Or, if you don't care about `Protocols` and abstract base classes:

```python
def get(svc_type: type[T]) -> T:
    return svcs.flask.get(svc_type)
```


## Credits

*svcs* is written by [Hynek Schlawack](https://hynek.me/) and distributed under the terms of the [MIT](./LICENSE) license.

The development is kindly supported by my employer [Variomedia AG](https://www.variomedia.de/) and all my amazing [GitHub Sponsors](https://github.com/sponsors/hynek).
