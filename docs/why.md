# Why?

A {term}`service locator` like *svcs* allows you to configure and manage all your {term}`service`s in *one central place*, access them in a *consistent* way without worrying about *cleaning them up* and achieve *loose coupling*.

---

In practice that means that at runtime, you say "*Give me a database connection*!", and *svcs* will give you whatever you've configured it to return when asked for a database connection.
This can be an actual database connection or it can be a mock object for testing.
All of this happens *within* your application – service locators are **not** related to {term}`service discovery`.

If you follow the **{term}`Dependency Inversion Principle`**, you would register concrete factories for abstract interfaces; in Python usually a [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol) or an [*abstract base class*](https://docs.python.org/3.11/library/abc.html).

If you follow the **{term}`Hexagonal Architecture`** (aka "*ports and adapters*"), the registered types are *ports* and the factories produce the *adapters*.
*svcs* gives you a well-defined way to make your application *pluggable*.

```{include} ../README.md
:start-after: "<!-- begin benefits -->"
:end-before: "<!-- end benefits -->"
```

If you don't shy away from some global state and your web framework supports it, you can go even further and write:

```python
def view():
    db, api, cache = svcs.flask.get(Database, WebAPIClient, Cache)
```

You set it up like this:

% skip: next

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
    ping=lambda conn: conn.execute(text("SELECT 1")), # ← health check
    on_registry_close=engine.dispose
)

@atexit.register
def cleanup():
    registry.close()  # calls engine.dispose()
```

The generator-based setup and cleanup may remind you of [*pytest* fixtures](https://docs.pytest.org/en/stable/explanation/fixtures.html).
The hooks that are defined as `on_registry_close` are called when you call `Registry.close()` – e.g. when your application is shutting down.

Next, if you've registered health checks (called *pings*) for your services, you can write a simple health check endpoint.
This is how it could look in Pyramid[^flask]:

[^flask]: See the [Flask integration](flask.md) chapter for a Flask equivalent.

```{literalinclude} examples/health_check_pyramid.py
```

Once written, you have to never touch this view endpoint again and define the service health checks *where you define the services*.

::: {important}
All of this may look over-engineered if you have only one or two services.
However, it starts paying dividends *very fast* once you go past that.
:::


## asyncio

*svcs* comes with **full async** support via a-prefixed methods (i.e. `aget()` instead of `get()`, et cetera).


## Static Typing

```{include} ../README.md
:start-after: "<!-- begin typing -->"
:end-before: "<!-- end typing -->"
```

## Is this Dependency Injection or Service Location!?

It can be both!
At its core, *svcs* is a {term}`service locator` because it locates services for you when you call `get()` – based on your configuration.

But it depends *where* you choose to call `get()` whether you're doing *dependency injection* or *service location* in the classical sense.

When people think of dependency injection, they usually think of *dependency injection frameworks* that use decorators or other magic to inject services into their code.
But that's **not** what dependency injection means.
It means the {term}`service layer` is called with all services it needs to do its job.

So, if you use *svcs* in your web view to look up a database connection and pass the database connection into your service layer, you're doing *dependency injection*.

On the other hand, if you use *svcs* in your service layer – or even business logic – to look up a database connection and use it there, you're doing *service location*.

We strongly recommend the former over the latter because it's much easier to test and reason about.

If you're curious, check the [glossary](glossary) entry for {term}`Service Locator` and {term}`Dependency Injection` for more details.


## Why not?

The main downside of service locators is that it's impossible to verify whether all required dependencies have been configured without running the code.

This is a consequence of being imperative instead of declarative and the main trade-off to make when deciding between a traditional dependency injection framework and a service locator like *svcs*.

If you still prefer a dependency injection framework, check out [*incant*](https://github.com/Tinche/incant) – a very nice package by a friend of the project.


## What Next?

If you're still interested, learn about our [core concepts](core-concepts) first – it's just two of them!

Once you've understood the life cycles of registries and containers, you can look our framework integrations that get you started in no time:

- [Flask](flask.md)
- [Pyramid](pyramid.md)
- Or learn how to write [your own](custom.md)!

If you get overwhelmed by the jargon, we have put a lot of effort into our [glossary](glossary)!
