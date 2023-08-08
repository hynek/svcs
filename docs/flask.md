# Flask

*svcs* has grown from my frustration with the repetitiveness of using the `get_x` that creates an `x` and then stores it on the `g` object [pattern](https://flask.palletsprojects.com/en/latest/appcontext/#storing-data).

Therefore it comes with Flask support out of the box in the form of the `svcs.flask` module.

It:

- puts the registry into `app.config["svcs_registry"]`,
- unifies the caching of services on the `g` object by putting a container into `g.svcs_container`,
- transparently retrieves them from there for you,
- and installs a [`teardown_appcontext()`](http://flask.pocoo.org/docs/latest/api#flask.Flask.teardown_appcontext) handler that calls `close()` on the container when a request is done.


## Initialization

You can add support for *svcs* by calling `svcs.flask.init_app(app)` in your [*application factory*](https://flask.palletsprojects.com/en/latest/patterns/appfactories/).
For instance, to create a factory that uses a SQLAlchemy engine to produce connections, you could do this:


% skip: start

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


## Service Acquisition

Now you can request the `Connection` object in your views:

```python
@app.get("/")
def index() -> flask.ResponseValue:
    conn = svcs.flask.get(Connection)
```

(flask-health)=

## Health Checks

The {func}`svcs.flask.get_pings` helper will transparently pick the container from `g`.
So, if you would like a [health endpoint](https://kubernetes.io/docs/reference/using-api/health-checks/), it could look like this:

```{literalinclude} examples/health_check_flask.py
```

(flask-testing)=

## Testing

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

::: {important}
The `replace_(factory|value)` method *requires* an application context and ensures that if a factory/value has already been created *and cached*, they're removed before the new factory/value is registered.

Possible situations where this can occur are *pytest* fixtures where you don't control the order in which they're called.
:::


## Quality of Life

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
    conn = services.get(Connection)
```

🧑‍🍳💋


## API Reference

### Application Life Cycle

```{eval-rst}
.. module:: svcs.flask

.. autofunction:: init_app
.. autofunction:: close_registry
```


### Registering and Overwriting Services

```{eval-rst}
.. autofunction:: register_factory
.. autofunction:: register_value
.. autofunction:: replace_factory
.. autofunction:: replace_value
```


### Service Acquisition

```{eval-rst}
.. function:: get(svc_types)

   Same as :meth:`svcs.Container.get()`, but uses container on :obj:`flask.g`.

.. autofunction:: get_abstract
.. autofunction:: get_pings
```
