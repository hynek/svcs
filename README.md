
# A Service Registry for Dependency Injection

> **Warning**
> ☠️ Not ready yet! ☠️
>
> Feedback is welcome, but everything can and will change until proclaimed stable.
>
> Currently only [**Flask** support](#flask) is production-ready, but details can still change.

*svc-reg* is a service registry for Python that lets you register factories for certain types and then create instances of those types with life-cycle management and health checks.

This allows you to configure and manage resources in *one central place* and access them in a consistent way.

That:

- enables **dependency injection**,
- simplifies **testing**,
- unifies **cleanups**,
- and allows for **easy health** checks across *all* resources.

No global mutable state necessary (but possible for extra comfort).


## Low-Level Core API

You're unlikely to use the core API directly, but it's good to know what's going on underneath.

*svc-reg* has two important concepts:

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

The values and return values of the factories don't have to be actually instances of the type they're registered for.
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

A container lives as long as you want the instances to live -- e.g. as long as a request lives.
At the end you run `container.close()` to cleanup all instances that the container has created.
You can use this to return database connections to a pool, et cetera.

If you have async cleanup functions, use `await container.aclose()` instead.
It will run both sync and async cleanup functions.

---

Additionally, each registered service may have a `ping` callable that can be used in a health check.
You can ask for all pingable registered services with `container.get_pings()`.
This returns a list of `ServicePing` objects that currently have a name property to identify the ping and a `ping` method that instantiates the service, adds it to the cleanup list, and runs the ping.

Importantly: It is possible to overwrite registered service factories later -- e.g. for testing -- **without monkey-patching**.
You have to make sure to remove possibly cached instances from the container if you're using nested dependencies (`Container.forget_service_type()`).
The Flask integration takes care of this for you.

---

Generally speaking, the `Registry` object should live on an application-scoped object like Flask's `app.config` object.
On the other hand, the `Container` object should live on a request-scoped object like Flask's `g` object or Pyramid's `request` object.


> **Note**
> The core APIs only use pure object without any global state but also without any comfort.
> It gets more interesting when using framework-specific integrations where the life-cycle of the Container and thus services is handled automatically.


## Flask

*svc-reg* has grown from my frustration of the repetitiveness of using the `get_x` that creates an `x` and then stores it on the `g` object [pattern](https://flask.palletsprojects.com/en/latest/appcontext/#storing-data).

Therefore it comes with Flask support out of the box in the form of the `svc_reg.flask` module.

You can add support for *svc-reg* by calling `svc_reg.flask.init_app(app)` in your [*application factory*](https://flask.palletsprojects.com/en/latest/patterns/appfactories/).
For instance to create a factory that uses an SQLAlchemy Engine to create Connections, you could do this:

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
    reg = svc_reg.Registry()
    app = svc_reg.flask.init_app(app, reg)

    # The registry lives in app.config["svc_registry"] now. If you don't pass it
    # explicitly, init_app creates one for you.

    # Now, register a factory that calls `engine.connect()` if you ask for a
    # Connections and `connection.close()` on cleanup.
    # If you ask for a ping, it will run `SELECT 1` on a new connection and
    # cleanup the connection behind itself.
    engine = create_engine("postgresql://localhost")
    ping = text("SELECT 1")
    reg.register_factory(
        Connection,
        engine.connect,
        cleanup=lambda conn: conn.close(),
        ping=lambda conn: conn.execute(ping)
    )

    # You also use svc_reg WITHIN factories:
    reg.register_factory(
        unit_of_work.UnitOfWork,
        lambda: unit_of_work.UnitOfWork.from_connection(
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
def index():
    conn: Connection = svc_reg.flask.get(Connection)
```

If you have an health endpoint, it could look like this:

```python
@bp.get("healthy")
def healthy() -> flask.ResponseValue:
    """
    Ping all external services.
    """
    ok: list[str] = []
    failing: list[dict[str, str]] = []
    code = 200

    for svc in services.get_pings():
        try:
            svc.ping()
            ok.append(svc.name)
        except Exception as e:
            failing.append({svc.name: repr(e)})
            code = 500

    return {"ok": ok, "failing": failing}, code
```

`init_app()` also installs an [`teardown_appcontext()`](http://flask.pocoo.org/docs/latest/api#flask.Flask.teardown_appcontext) handler that calls `close()` on the container when a request is done.


### Testing

Now if you want the database to return a mock `Connection`, you can do this:

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

        # Overwrite the Connection factory with the Mock.
        # This is all it takes to mock the database.
        reg_svc.flask.register_value(Connection, conn)

        # Now, the endpoint should return a 500.
        response = app.test_client().get("/")
        assert response.status_code == 500
```


### Quality of Life

In practice, you can simplify / beautify the code within your views by creating a `services` module that re-exports those Flask helpers.

Say this is `app/services.py`:

```python
from svc_reg.flask import (
    get,
    get_pings,
    init_app,
    register_factory,
    register_value,
)


__all__ = [
    "get_pings",
    "get",
    "init_app",
    "register_factory",
    "register_value",
]
```

Now you can register services in your application factory like this:

```python
from app import services

services.register_factory(Connection, ...)
```

And you get them in your views like this::

```python
from app import services

@app.route("/")
def index():
    conn: Connection = services.get(Connection)
```

🧑‍🍳💋


## Caveats

One would expect the the `Container.get()` method would have a type signature like `get(type: type[T]) -> T`.
Unfortunately, that's currently impossible, because it [precludes the usage of `Protocols` as service types](https://github.com/python/mypy/issues/4717) which would make the package pointless.

Therefore it returns `Any` and until Mypy changes its stance, you have to use it like this:

```python
conn: Connection = container.get(Connection)
```


## Credits

*stamina* is written by [Hynek Schlawack](https://hynek.me/) and distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

The development is kindly supported by my employer [Variomedia AG](https://www.variomedia.de/) and all my amazing [GitHub Sponsors](https://github.com/sponsors/hynek).
