<!-- begin-pypi -->

# A Service Registry for Dependency Injection

> **Warning**
> ☠️ Not ready yet! ☠️
>
> This project is only public to [gather feedback](https://github.com/hynek/svc-reg/discussions), and everything can and will change until the project is proclaimed stable.
>
> Currently only [**Flask** support](#flask) is production-ready, but API details can still change.
>
> At this point, it's unclear whether this project will become a "proper Hynek project".
> I will keep using it for my work projects, but whether this will grow beyond my personal needs depends on community interest.

*svc-reg* is a [service locator](https://en.wikipedia.org/wiki/Service_locator_pattern) for Python that lets you register factories for types/interfaces and then create instances of those types with unified life-cycle management and health checks.

**This allows you to configure and manage resources in *one central place* and access them in a *consistent* way.**

The idea is that at runtime, you say, for example, "*Give me a database connection*!", and *svc-reg* will give you one, depending on how you configured it.
If you like the [*Dependency Inversion Principle*](https://en.wikipedia.org/wiki/Dependency_inversion_principle) (aka "*program against interfaces, not implementations*"), you would register concrete factories for abstract interfaces[^abstract].

[^abstract]: In Python usually a [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol) or an [Abstract Base Class](https://docs.python.org/3.11/library/abc.html).

That:

- enables **dependency injection**,
- simplifies **testing**,
- unifies **cleanups**,
- and allows for **easy health** checks across *all* resources.

No global mutable state is necessary – but possible for extra comfort.

The goal is to minimize your business code to:

```python
def view(request):
    db = request.services.get(Database)
    api = request.services.get(WebAPIClient)
```

or even:

```python
def view():
    db = services.get(Database)
    api = services.get(WebAPIClient)
```

The latter already works with [Flask](#flask).

<!-- end-pypi -->


## Low-Level Core API

You're unlikely to use the core API directly, but knowing what's happening underneath is good to dispel any concerns about magic.

*svc-reg* has two essential concepts:

A **`Registry`** allows to register factories for certain types.
It's expected to live as long as your application lives.
Its only job is to store and retrieve factories.

It is possible to register either factories or values:

```python
>>> import svc_reg
>>> import uuid

>>> reg = svc_reg.Registry()

>>> reg.register_factory(uuid.UUID, uuid.uuid4)
>>> reg.register_value(str, "Hello World")

```

The values and return values of the factories don't have to be actual instances of the type they're registered for.
But the types must be *hashable* because they're used as keys in a lookup dictionary.

---

A **`Container`** belongs to a Registry and allows to create instances of the registered types and takes care of their life-cycle:

```python
>>> container = svc_reg.Container(reg)

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

A container lives as long as you want the instances to live -- e.g., as long as a request lives.
At the end, you run `container.close()` to clean up all instances that the container has created.
You can use this to return database connections to a pool, et cetera.

If you have async cleanup functions, use `await container.aclose()` instead.
It will run both sync and async cleanup functions.

Failing cleanups are logged at `warning` level but otherwise ignored.

---

Additionally, each registered service may have a `ping` callable that you can use for health checks.
You can request all pingable registered services with `container.get_pings()`.
This returns a list of `ServicePing` objects that currently have a name property to identify the ping and a `ping` method that instantiates the service, adds it to the cleanup list, and runs the ping.

Importantly: It is possible to overwrite registered service factories later -- e.g., for testing -- **without monkey-patching**.
You have to remove possibly cached instances from the container if you're using nested dependencies (`Container.forget_service_type()`).
The Flask integration takes care of this for you.

How to achieve this in other frameworks elegantly is TBD.

---

Generally, the `Registry` object should live on an application-scoped object like Flask's `app.config` object.
On the other hand, the `Container` object should live on a request-scoped object like Flask's `g` object or Pyramid's `request` object.


> **Note**
> The core APIs only use vanilla objects without any global state but also without any comfort.
> It gets more interesting when using framework-specific integrations where the life-cycle of the container and, thus, services is handled automatically.


## Flask

*svc-reg* has grown from my frustration with the repetitiveness of using the `get_x` that creates an `x` and then stores it on the `g` object [pattern](https://flask.palletsprojects.com/en/latest/appcontext/#storing-data).

Therefore it comes with Flask support out of the box in the form of the `svc_reg.flask` module.
It:

- puts the registry into `app.config["svc_registry"]`,
- unifies the putting and caching of services on the `g` object by putting a container into `g.svc_container`,
- transparently retrieves them from there for you,
- and installs a [`teardown_appcontext()`](http://flask.pocoo.org/docs/latest/api#flask.Flask.teardown_appcontext) handler that calls `close()` on the container when a request is done.

---

You can add support for *svc-reg* by calling `svc_reg.flask.init_app(app)` in your [*application factory*](https://flask.palletsprojects.com/en/latest/patterns/appfactories/).
For instance, to create a factory that uses a SQLAlchemy engine to produce connections, you could do this:

```python
from flask import Flask
from sqlalchemy import Connection
from sqlalchemy.sql import text

import svc_reg


def create_app(config_filename):
    app = Flask(__name__)
    app.config.from_pyfile(config_filename)

    ##########################################################################
    # Set up the registry using Flask integration.
    app = svc_reg.flask.init_app(app)

    # Now, register a factory that calls `engine.connect()` if you ask for a
    # Connections and `connection.close()` on cleanup.
    # If you ask for a ping, it will run `SELECT 1` on a new connection and
    # clean up the connection behind itself.
    engine = create_engine("postgresql://localhost")
    ping = text("SELECT 1")
    svc_reg_flask.register_factory(
        # The app argument makes it good for custom init_app() functions.
        app,
        Connection,
        engine.connect,
        cleanup=lambda conn: conn.close(),
        ping=lambda conn: conn.execute(ping)
    )

    # You also use svc_reg WITHIN factories:
    svc_reg_flask.register_factory(
        app, # <---
        AbstractRepository,
        lambda: Repository.from_connection(
            svc_reg.flask.get(Connection)
        ),
    )
    ##########################################################################

    from yourapplication.views.admin import admin
    from yourapplication.views.frontend import frontend
    app.register_blueprint(admin)
    app.register_blueprint(frontend)

    return app
```

Now you can request the `Connection` object in your views:

```python
@app.route("/")
def index() -> flask.ResponseValue:
    conn: Connection = svc_reg.flask.get(Connection)
```

If you have a health endpoint, it could look like this:

```python
@app.get("healthy")
def healthy() -> flask.ResponseValue:
    """
    Ping all external services.
    """
    ok: list[str] = []
    failing: list[dict[str, str]] = []
    code = 200

    for svc in svc_reg.flask.get_pings():
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

> **Note**
> The `replace_(factory|value)` method *requires* an application context and ensures that if a factory/value has already been created *and cached*, they're removed before the new factory/value is registered.
>>
> Possible situations where this can occur are Pytest fixtures where you don't control the order in which they're called.


### Quality of Life

In practice, you can simplify/beautify the code within your views by creating a `services` module that re-exports those Flask helpers.

Say this is `app/services.py`:

```python
from svc_reg.flask import (
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
Unfortunately, that's currently impossible because it [precludes the usage of `Protocols` as service types](https://github.com/python/mypy/issues/4717), making this package pointless.

Therefore it returns `Any`, and until Mypy changes its stance, you have to use it like this:

```python
conn: Connection = container.get(Connection)
```


## Credits

*svc-reg* is written by [Hynek Schlawack](https://hynek.me/) and distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

The development is kindly supported by my employer [Variomedia AG](https://www.variomedia.de/) and all my amazing [GitHub Sponsors](https://github.com/sponsors/hynek).
