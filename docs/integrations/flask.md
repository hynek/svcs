# Flask

*svcs*'s [Flask](https://flask.palletsprojects.com/) integration uses the {attr}`flask.Flask.config` object to store the {class}`svcs.Registry` and the {obj}`~flask.g` object to store the {class}`svcs.Container`.
It also installs a {meth}`flask.Flask.teardown_appcontext` handler to close the container when the request is done.

---

*svcs*'s origin story is the frustration over the repetitiveness of the "write a `get_X` that creates an `X` and then stores it on `g` and register clean up -- for every single `X`"-[pattern](https://flask.palletsprojects.com/en/latest/appcontext/#storing-data), so let's have a quick look at its problems for motivation.

You can [skip this section](#flask-init) if you'd rather see solutions than problems.

(flask-get-x)=

## The Problems with the `get_X` Pattern

% skip: next

```python
from flask import g

def get_db():
    if 'db' not in g:
        g.db = connect_to_database()

    return g.db

@app.teardown_appcontext
def teardown_db(exception):
    db = g.pop('db', None)

    if db is not None:
        db.close()
```

Here, we have a `get_db` function that creates a database connection and stores it on {obj}`~flask.g` so that it can be reused later.
If you ask again, it returns the same connection from `g`.

At the same time, it registers a {meth}`~flask.Flask.teardown_appcontext` handler that, at the end of a request, looks at `g` for the connection and closes it -- if it finds one.


If you need to replace the database connection with a mock in tests, the canonical way is using {obj}`flask.appcontext_pushed`.
In pytest it could look like this:

```python
from contextlib import contextmanager
from flask import appcontext_pushed

@contextmanager
def db_set(app, db):
    def handler(sender, **kwargs):
        g.db = db  # ← setting g.db here prevents get_db setting it itself
    with appcontext_pushed.connected_to(handler, app):
        yield

class Boom:
    def __getattr__(self, name):
        """Just raise an exception when you try to use it."""
        raise RuntimeError("Boom!")

def test_broken_db(app):
    with db_set(app, Boom()):
        c = app.test_client()
        resp = c.get('/some-url')

        assert 500 == resp.status_code
```

This pattern is repeated for **_every dependency_** you have and has multiple problems:

- **Loads of boilerplate**.
  We've taken this example straight from the Flask docs, and you can see that only 2 out of 10 lines are relevant to the dependency it handles.
  This example is quite simple, but imagine you have ten dependencies.

- We've found that the necessity to import `get_db` from the place it's defined often leads to **circular imports** and **tight coupling**.

- It puts Flask-specific code **where it doesn't belong**:
  into a module that handles database connections.

- The **naming** of the dependency and the function that creates it is **ad hoc**.
  If you write other dependencies, you must be careful about naming clashes.
  At the same time, if your other dependency wants to use the database, it has to import and call `get_db`.

- Looking at **all dependencies** in your app is only possible with *even more* boilerplate.

- Calling `get_db` outside of a **request context** raises an **opaque error**.

- It's awkward to make `get_db` return **test objects**.
  `appcontext_pushed` is a (boilerplate-rich!) hack that's not even documented in the narrative Flask docs, and we claim that most people don't understand how it works in the first place.

**These** were the reasons why Hynek started writing *svcs* before adding more integrations, initially just as a module that got copy-pasted between work projects.
It solves all of the above problems and more.

:::{important}
Given that Flask is a *micro*-framework, this is not meant as a critique of the project.
It's meant as an explanation why we need *svcs* just like any other Flask extension.
:::

(flask-init)=

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
    svcs.flask.register_factory(
        # The app argument makes it good for custom init_app() functions.
        app,
        Connection,
        connection_factory,
        ping=lambda conn: conn.execute(ping),
        on_registry_close=engine.dispose,
    )

    # You also use svcs WITHIN factories:
    svcs.flask.register_factory(
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

You can also use the {obj}`svcs.flask.container` local proxy:

```python

from svcs.flask import container

@app.get("/")
def index() -> flask.ResponseValue:
    conn = container.get(Connection)
```

(flask-health)=

## Health Checks

The {func}`svcs.flask.get_pings` helper will transparently pick the container from `g`.
So, if you would like a health endpoint, it could look like this:

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

        assert 500 == response.status_code
```

{meth}`svcs.flask.overwrite_value`  makes sure that the instantiation cache of the active container is cleared, such that possibly existing connections that you've used in setup are closed and removed.


## Quality of Life

In practice, you can simplify/beautify the code within your views by creating a module that re-exports those Flask helpers.

Say this is `your_app/services.py`:

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
.. autofunction:: get_registry
.. autofunction:: close_registry
.. attribute:: registry

   A :class:`werkzeug.local.LocalProxy` that transparently calls :func:`get_registry` on :obj:`flask.current_app`.

   .. versionadded:: 23.21.0
```


### Registering Services

```{eval-rst}
.. autofunction:: register_factory
.. autofunction:: register_value
```


### Service Acquisition

```{eval-rst}
.. autofunction:: svcs_from
.. attribute:: container

   A :class:`werkzeug.local.LocalProxy` that transparently calls :func:`svcs_from` for you when accessed within a request context.
.. function:: get(svc_types)

   Same as :meth:`svcs.Container.get()`, but uses the container from :obj:`flask.g`.

.. autofunction:: get_abstract
.. autofunction:: get_pings
```


### Testing

:::{caution}
These functions should not be used in production code.

They always reset the container and run all cleanups when overwriting a service.

See also {ref}`flask-testing`.
:::

```{eval-rst}
.. autofunction:: overwrite_factory
.. autofunction:: overwrite_value
```
