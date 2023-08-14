# Flask

*svcs*'s [Flask](https://flask.palletsprojects.com/en/2.3.x/) integration uses the {attr}`flask.Flask.config` object to store the {class}`svcs.Registry` and the {obj}`~flask.g` object to store the {class}`svcs.Container`.
It also installs a {meth}`flask.Flask.teardown_appcontext` handler to close the container when the request is done.

The origin story of *svcs* is the frustration over the repetitiveness of the "write a `get_x` that creates an `x` and then stores it on `g` and register clean up -- for every single `x`" [pattern](https://flask.palletsprojects.com/en/latest/appcontext/#storing-data).


## Initialization

You add support for *svcs* to your Flask app by calling {meth}`svcs.flask.init_app` in your [*application factory*](inv:flask#patterns/appfactories).
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

```{literalinclude} ../examples/flask/health_check.py
```

(flask-testing)=

## Testing

Having a central place for all your services makes it obvious where to mock them for testing.
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

        ######################################################################
        # Overwrite the Connection factory with the Mock.
        # This is all it takes to mock the database.
        svcs.flask.overwrite_value(Connection, conn)
        ######################################################################

        # Now, the endpoint should return a 500.
        response = app.test_client().get("/")
        assert response.status_code == 500
```

{meth}`svcs.flask.overwrite_value`  makes sure that the instantiation cache of the active container is cleared, such that possibly existing connections that you've used in setup are closed and removed.


## Quality of Life

In practice, you can simplify/beautify the code within your views by creating a `services` module that re-exports those Flask helpers.

Say this is `app/services.py`:

```python
from svcs.flask import (
    close_registry,
    get,
    get_pings,
    init_app,
    overwrite_factory,
    overwrite_value,
    register_factory,
    register_value,
    svcs_from,
)


__all__ = [
    "close_registry",
    "get_pings",
    "get",
    "init_app",
    "overwrite_factory",
    "overwrite_value",
    "register_factory",
    "register_value",
    "svcs_from",
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
.. autofunction:: overwrite_factory
.. autofunction:: overwrite_value
```


### Service Acquisition

```{eval-rst}
.. autofunction:: svcs_from
.. function:: get(svc_types)

   Same as :meth:`svcs.Container.get()`, but uses the container from :obj:`flask.g`.

.. autofunction:: get_abstract
.. autofunction:: get_pings
```
