# Why?

{attribution="Brandon Rhodes"}
> Monkey patching is software bankruptcy.

*svcs* (pronounced *services*) gives you unified and ergonomic API for storing and retrieving objects to and from your web application's **request objects**.
Additionally, it ensures that those objects get **cleaned up** when the request is done, offers hooks that make your application more **testable**, and gives you live **introspection** of their health.

This documentation mostly talks in terms of web applications because they are the most common use-case for packages like this.
However, *svcs* is useful for any application that can benefit from {term}`late binding` and being pluggable.
The word *flexible* is part of the project's tagline for a reason!
It's bound neither to request objects nor to web applications.

---

More formally: *svcs* is a {term}`service locator`.
Service locators like *svcs*  allow you to configure and manage all your {term}`service`s in *one central place*, acquire them in a *consistent* way without worrying about *cleaning them up*, and thus achieve *loose coupling*.
That gives you a well-defined place and method for storing -- *and replacing!* -- your application's configurable dependencies.

:::{admonition} Terminology
:class: tip

If the term **_service_** seems confusing to you, it's because it is.
The term is so overloaded in software engineering that it can mean everything and nothing.
But it's the correct term, so we're using it to avoid making things even more confusing.

If you want the full scoop, we have an extensive glossary that explains what we mean by {term}`service` in the context of *svcs*.
But for now, you can think of it as a **configurable dependency** that your application needs to do things like accessing databases or web APIs, and you'll be able to follow along just fine.

Service location is **not** related to {term}`service discovery`.
:::


## Modus Operandi

In practice, you say "*svcs*, give me a database connection!" once you need a database connection, and *svcs* will give you whatever you've configured to return when asked for a database connection.
That can be an actual database connection, or it can be a fake test object.

A key feature of service locators is that you only ask for the services once you *know* that you will need them.
So you don't have to pre-instantiate all services just in case (*wasteful*!) or move the instantiation further into, for example, your web views (*onerous resource management*!).

If you follow the **{term}`Dependency Inversion Principle`**, you would register concrete factories for abstract interfaces.
In Python, that would be usually a [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol) or an [*abstract base class*](https://docs.python.org/3/library/abc.html).

If you follow the **{term}`Hexagonal Architecture`** (aka "*ports and adapters*"), the registered types are *ports*, and the factories produce the *adapters*.

Here's how this looks in practice with our various integrations:

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

The callbacks defined as `on_registry_close` are called when you call {meth}`svcs.Registry.close()` -- for example, when your application is shutting down or after a test.

Next, you can write a simple health check endpoint if you've registered health checks (called *pings*) for your services.
This is how it could look with the shipped integrations:

```{include} core-concepts.md
:start-after: "<!-- begin health checks -->"
:end-before: "<!-- end health checks -->"
```

Once written, you never touch this view endpoint again and define the service health checks *where you define the services*.

::: {important}
All of this may look over-engineered if you have only one or two services.
However, it starts paying dividends *very fast* once you go past that.
:::


## asyncio

*svcs* comes with **full async** support via a-prefixed methods (like `aget()` instead of `get()`, and so on).

In fact, most of our {doc}`integrations/index` are for async frameworks!


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


## Benefits

While it may take a moment to realize, all of this comes with many benefits:

**Reduction in boilerplate.**
Every web framework has some way to store data on long-lived objects like the application, and short-lived objects like requests (for example, in Flask it's {attr}`flask.Flask.config` and {obj}`flask.g` – Starlette uses `request.state` for both).
Some frameworks also have helpers to control the lifecycle of those objects (like {meth}`flask.Flask.teardown_appcontext` or {meth}`pyramid.request.Request.add_finished_callback`).
But they work subtly differently and you accumulate a lot of repetitive boilerplate code.
In fact, Hynek started this project because of the [repetitiveness of Flask's `get_X` pattern](#flask-get-x).

**Unification of acquisition and release.**
Knowing where to find your services, how to acquire them, and not caring about their cleanup makes your application more robust and easier to reason about.
It also makes it easier to write reusable middleware because you don't have to remember where a dependency it needs is stored on the request object (or was it on the application object!?).
With *svcs* you just have to remember its *type* and gain a portable API for pluggable dependencies.

**Type safety.**
Since you're asking for objects of certain types, *svcs* can ensure that Mypy knows that the returned object is of that type.
You can cheat, of course, by returning something else -- *svcs* doesn't care.
And, of course, type hints are optional -- *svcs* is just as valuable without them.

**Unintrusive testing through loose coupling.**
As per Brandon's quote at the beginning of this section, monkey-patching is software bankruptcy.
Adding {term}`late binding` to your application allows you to replace your dependencies with test objects in a well-defined, debuggable way.
Just create your application and overwrite the service configurations before you perform your tests as necessary.

**Health checks.**
A production-ready application should be able to tell you whether it -- and all its external dependencies -- is healthy.
Having that exposed as a web endpoint is great for monitoring and debugging.
Providing a health endpoint without a centralized registry of services is highly boilerplate-heavy.
With *svcs* you get that for free.


## Why not?

The main downside of service locators is that it's only possible to verify whether all required dependencies have been configured by running the code.

That's a consequence of {term}`late binding` happening *imperatively* and the main trade-off when deciding between a service locator like *svcs* and a traditional dependency injection framework that is usually *declarative* and knows the requirements ahead of time.

We believe the upsides of service locators outweigh the downsides and that avoiding late binding problems is easy.
For instance, by configuring the same service in the same place for all environments.

If you still prefer a dependency injection framework, check out [*incant*](https://github.com/Tinche/incant) -- a lovely package by a friend of the project.


## What Next?

If you're still interested, learn about our [core concepts](core-concepts) first -- it's just two of them!

Once you've understood the life cycles of registries and containers, you can look our [framework integrations](integrations/index.md) which should get you started right away.

Whenever you get overwhelmed by the jargon, we have put much effort into our [glossary](glossary)!
