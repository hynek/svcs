# Flask Tutorial

In this tutorial we'll build a simple Flask application that uses *svcs* to manage its services.
We won't start at zero, but we'll assume that you already have a Flask application that uses the [`get_X` pattern](https://flask.palletsprojects.com/en/latest/appcontext/#storing-data) and look at the problems that come with it.
Then we'll see how *svcs* can help us solve those problems.

## The Problems with the `get_X` Pattern

The default pattern to manage dependencies in Flask is to use the [`get_X` pattern](https://flask.palletsprojects.com/en/latest/appcontext/#storing-data):

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

Here we have a `get_db` function that creates a database connection and stores it on {obj}`~flask.g` so that it can be reused later.
If you ask again, it returns the same connection from `g`.

At the same time, it registers a {meth}`flask.Flask.teardown_appcontext` handler that looks at `g` for the connection and closes it when the request is done.


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

This pattern is repeated for every dependency you have and has multiple problems:

- **Loads of boilerplate**.
  We've taken this example straight from the Flask docs and you can see that only 2 out of 10 lines are actually relevant to the dependency it's handling.
  This example is quite simple, but imagine you have 10 dependencies.

- We've found that the necessity to import `get_db` from the place it's defined often leads to **circular imports** and **tight coupling**.

- It puts Flask-specific code **where it doesn't belong**:
  into a module that handles database connections.

- Calling `get_db` outside of a **request context** raises an **opaque error**.

- The **naming** of the dependency and the function that creates it is **ad-hoc**.
  If you write other dependencies, you have to be careful about naming clashes.
  At the same time if your other dependency wants to use the database, it has to import and call `get_db`.

- Looking at **all dependencies** in your app is impossible without even more boilerplate.

- It's awkward to make `get_db` return **test objects**.
  `appcontext_pushed` is a (boilerplate-rich!) hack that's not even documented in the narrative Flask docs and we pose that most people don't understand how it works at all.

**This** was the reason why Hynek started writing *svcs* -- originally just as an module that got copy-pasted between work projects.

:::{important}
Given that Flask is a *micro*-framework, this is not meant as a critique of the project.
It's meant as an explanation why we need *svcs* just like any other Flask extension.
:::

So next, let's see how *svcs* can help us improve the situation!


## *svcs* to the Rescue

...
