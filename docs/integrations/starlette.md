# Starlette

*svcs*'s [Starlette](https://www.starlette.io/) integration stores the {class}`svcs.Registry` on the *lifespan state* and the {class}`svcs.Container` is added to the request state using a [pure ASGI middleware](https://www.starlette.io/middleware/#pure-asgi-middleware).

It's a great way to get type-safety and rich life cycle management on top of Starlette's low-level dependency capabilities.

(starlette-init)=

## Initialization

To use *svcs* with Starlette, you have to pass a [*lifespan*](https://www.starlette.io/lifespan/) -- that has been wrapped by {class}`svcs.starlette.lifespan` -- and a {class}`~svcs.starlette.SVCSMiddleware` to your application:

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware

import svcs


@svcs.starlette.lifespan
async def lifespan(app: Starlette, registry: svcs.Registry):
    registry.register_factory(Database, Database.connect)

    yield {"your": "other stuff"}

    # Registry is closed automatically when the app is done.


app = Starlette(
    lifespan=lifespan,
    middleware=[Middleware(svcs.starlette.SVCSMiddleware)],
    routes=[...],
)
```

(starlette-get)=

## Service Acquisition

You can either use {func}`svcs.starlette.svcs_from`:

```python
from svcs.starlette import svcs_from

async def view(request):
    db = await svcs_from(request).aget(Database)
```

Or you can use {func}`svcs.starlette.aget` to extract your services directly:

```python
import svcs

async def view(request):
    db = await svcs.starlette.aget(request, Database)
```

(starlette-health)=

## Health Checks

As with services, you have the option to either {func}`svcs.starlette.svcs_from` on the request or go straight for {func}`svcs.starlette.get_pings`.

A health endpoint could look like this:

```{literalinclude} ../examples/starlette/health_check.py
```

## Testing

The centralized service registry makes it straight-forward to selectively replace dependencies within your application in tests even if you have many dependencies to handle.

Let's take this simple application as an example:

```{literalinclude} ../examples/starlette/simple_starlette_app.py
```

Now if you want to make a request against the `get_user` view, but want the database to raise an error to see if it's properly handled, you can do this:

```{literalinclude} ../examples/starlette/test_simple_starlette_app.py
```

As you can see, we can inspect the decorated lifespan function to get the registry that got injected and you can overwrite it later.

::: {important}
You must overwrite *after* the application has been initialized.
Otherwise the lifespan function overwrites your settings.
:::


## Cleanup

If you initialize the application with a lifespan and middleware as shown above, and use {func}`~svcs.starlette.svcs_from` or {func}`~svcs.starlette.aget` to get your services, everything is cleaned up behind you automatically.


## API Reference

### Application Life Cycle

```{eval-rst}
.. module:: svcs.starlette

.. autoclass:: lifespan(lifespan)
.. autoclass:: SVCSMiddleware

.. seealso:: :ref:`fastapi-init`
```


### Service Acquisition

```{eval-rst}
.. function:: aget(request: starlette.requests.Request, svc_type1: type, ...)
   :async:

   Same as :meth:`svcs.Container.aget`, but uses the container from *request*.
.. autofunction:: aget_abstract
.. autofunction:: svcs_from
.. autofunction:: get_pings
```
