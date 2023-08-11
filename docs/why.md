# Why?

A {term}`service locator` like *svcs* allows you to configure and manage all your {term}`service`s in *one central place*, access them in a *consistent* way without worrying about *cleaning them up* and achieve *loose coupling*.


## Modus Operandi

In practice, that means that you say "*Give me a database connection*!" at runtime, and *svcs* will give you whatever you've configured to return when asked for a database connection.
That can be an actual database connection, or it can be a mock object for testing.
All this happens *within* your application -- service locators are **not** related to {term}`service discovery`.

A key feature of service locators is that you only ask for the services once you *know* that you will need them.
So you don't have to pre-instantiate all services just in case (*wasteful*!), or move the instantiation further into, for example, your web views (*resource management*!).

---

If you follow the **{term}`Dependency Inversion Principle`**, you would register concrete factories for abstract interfaces.
In Python, usually a [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol) or an [*abstract base class*](https://docs.python.org/3.11/library/abc.html).

If you follow the **{term}`Hexagonal Architecture`** (aka "*ports and adapters*"), the registered types are *ports*, and the factories produce the *adapters*.
*svcs* gives you a well-defined way to make your application *pluggable*.

```{include} ../README.md
:start-after: "<!-- begin benefits -->"
:end-before: "<!-- end benefits -->"
```

```{include} index.md
:start-after: "<!-- begin tabbed teaser -->"
:end-before: "<!-- end tabbed teaser -->"
```

To a type checker like [Mypy](https://mypy-lang.org), `db` has the type `Database`, `api` has the type `WebAPIClient`, and `cache` has the type `Cache`.

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
However, internally *svcs* uses context managers to manage cleanups, and if you pass a generator, it just wraps it with {func}`~contextlib.contextmanager` for your convenience.
But of course, you can directly pass a context manager as a factory, too, and the following is equivalent to the above:

% skip: next

```python
engine = create_engine("postgresql://localhost")

registry = svcs.Registry()
registry.register_factory(
    Connection,
    engine.connect,  # ← sqlalchemy.Connection is a context manager
    ping=lambda conn: conn.execute(text("SELECT 1")),
    on_registry_close=engine.dispose
)

@atexit.register
def cleanup():
    registry.close()
```

The automatic entering of context managers can be disabled on registration if you need control over when they're entered (for example, for database transaction managers).

The callbacks defined as `on_registry_close` are called when you call `Registry.close()` -- for example, when your application is shutting down.

Next, you can write a simple health check endpoint if you've registered health checks (called *pings*) for your services.
This is how it could look with the shipped integrations:

::: {tab} AIOHTTP
```{literalinclude} examples/aiohttp/health_check.py
```
:::
::: {tab} FastAPI
```{literalinclude} examples/fastapi/health_check.py
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

Once written, you never touch this view endpoint again and define the service health checks *where you define the services*.

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

It can be both, depending on your perspective!
At its core, *svcs* is a {term}`service locator` because it locates services for you when you call `get()` -- based on your configuration.

But it depends *where* you choose to call `get()` whether you're doing *dependency injection* or *service location* in the classical sense.

When people think of dependency injection, they usually think of *dependency injection frameworks* that use decorators, parameter inspection, and other magic to inject services automatically into their code.
But that's **not** what dependency injection means.
It means that a piece of code doesn't instantiate its dependencies itself and is called with all services it needs to do its job (also known as {term}`Inversion of Control`).

Therefore, if you use *svcs* in your web view to look up a database connection and pass the database connection into your {term}`service layer`, you're doing *dependency injection* for the arguably most important part of your application.
You have moved your {term}`composition root` into the web view, which allows you to be more flexible with the acquisition of your services while maintaining loose coupling between your service layer and its dependencies.

On the other hand, if you use *svcs* in your service layer -- or even business logic -- to look up a database connection and use it there, you're doing *service location*.

We strongly recommend the former over the latter because it's much easier to test and reason about.

If you're curious, check the [glossary](glossary) entries for {term}`Service Locator` and {term}`Dependency Injection` for more details.


## Why not?

The main downside of service locators is that it's impossible to verify whether all required dependencies have been configured without running the code.

That's a consequence of being imperative instead of declarative and the main trade-off when deciding between a traditional dependency injection framework and a service locator like *svcs*.

If you still prefer a dependency injection framework, check out [*incant*](https://github.com/Tinche/incant) -- a very nice package by a friend of the project.


## What Next?

If you're still interested, learn about our [core concepts](core-concepts) first -- it's just two of them!

Once you've understood the life cycles of registries and containers, you can look our [framework integrations](integrations/index.md) which should get you started right away.

If you get overwhelmed by the jargon, we have put much effort into our [glossary](glossary)!
