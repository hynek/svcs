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

% skip: next

```python
@view_config(route_name="healthy")
def healthy_view(request: Request) -> Response:
    ok: list[str] = []
    failing: list[dict[str, str]] = []
    status = 200

    for svc in request.svcs.get_pings():
        try:
            svc.ping()
            ok.append(svc.name)
        except Exception as e:
            failing.append({svc.name: repr(e)})
            status = 500

    return Response(
        content_type="application/json",
        status=status,
        body=json.dumps({"ok": ok, "failing": failing}).encode("ascii"),
    )
```

Once written, you have to never touch this view endpoint again and define the service health checks *where you define the services*.

::: {important}
All of this may look over-engineered if you have only one or two resources.
However, it starts paying dividends *very fast* once you go past that.
:::


## asyncio

*svcs* comes with **full async** support via a-prefixed methods (i.e. `aget()` instead of `get()`, et cetera).


## Static Typing

```{include} ../README.md
:start-after: "<!-- begin typing -->"
:end-before: "<!-- end typing -->"
```

## Is this Dependency Injection!?

No.

Although the concepts are related and share the idea of having a central registry of services, the ways they provide those services are fundamentally different:
{term}`Dependency injection` always passes your dependencies as arguments while you actively ask a service locator for them *when you need them*.

If you're curious, check the [glossary](glossary) entry for {term}`Service Locator` for more details.


## Why not?

The main downside of service locators is that it's impossible to verify whether all required dependencies have been configured without running the code.

This is a consequence of being imperative instead of declarative and the main trade-off to make when deciding between dependency injection and service locators.

If you still prefer dependency injection, check out [*incant*](https://github.com/Tinche/incant) – a very nice package by a friend of the project.


## What Next?

If you're still interested, learn about our [core concepts](core-concepts) first – it's just two of them!

Once you've understood the life cycles of registries and containers, you can look our framework integrations that get you started in no time:

- [Flask](flask)
- [Pyramid](pyramid)
- Or learn how to write [your own](custom)!

If you get overwhelmed by the jargon, always feel free to check our [glossary](glossary)!
