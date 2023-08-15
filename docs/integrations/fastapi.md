# FastAPI

*svcs*'s *centralization* and *on-demand* capabilities are a great complement to FastAPI's dependency injection system – especially when the annotated decorator approach becomes unwieldy because of too many dependencies.

*svcs*'s [FastAPI](https://fastapi.tiangolo.com) integration stores the {class}`svcs.Registry` on the *lifespan state* and the {class}`svcs.Container` is a [dependency](https://fastapi.tiangolo.com/tutorial/dependencies/) that can be injected into your views.
That makes very little API necessary from *svcs* itself.

(fastapi-init)=

## Initialization

FastAPI inherited the [`request.state`](https://www.starlette.io/requests/#other-state) attribute from [*starlette*](https://www.starlette.io/) and *svcs* uses it to store the {class}`svcs.Registry` on it.

To get it there you have to instantiate your FastAPI application with a *lifespan*.
Whatever this lifespan yields, becomes the initial request state via shallow copy.

To keep track of its registry for later overwriting, *svcs* comes with the {class}`svcs.fastapi.lifespan` decorator that remembers the registry on the lifespan object (see below in testing to see it in action):

```python
from fastapi import FastAPI

import svcs


@svcs.fastapi.lifespan
async def lifespan(app: FastAPI, registry: svcs.Registry):
    registry.register_factory(Database, Database.connect)

    yield {"your": "other", "initial": "state"}

    # Registry is closed automatically when the app is done.


app = FastAPI(lifespan=lifespan)
```

::: {seealso}
- [Lifespan state](https://www.starlette.io/lifespan/) in *starlette* documentation.
- [Lifespan](https://fastapi.tiangolo.com/advanced/events/) in FastAPI documentation (more verbose, but doesn't mention lifespan state).
:::

(fastapi-get)=

## Service Acquisition

*svcs* comes with the {func}`svcs.fastapi.container` dependency that will inject a request-scoped {class}`svcs.Container` into your views if the application is correctly initialized:

```python
from typing import Annotated

from fastapi import Depends


@app.get("/")
async def index(services: Annotated[svcs.Container, Depends(svcs.fastapi.container)]):
    db = services.get(Database)
```

For your convenience, *svcs* comes with the alias {class}`svcs.fastapi.DepContainer` that allows you to use the shorter and even nicer:

```python
@app.get("/")
async def index(services: svcs.fastapi.DepContainer):
    db = services.get(Database)
```

(fastapi-health)=

## Health Checks

With the help of the {func}`svcs.fastapi.container` dependency you can easily add a health check endpoint to your application without any special API:

```{literalinclude} ../examples/fastapi/health_check.py
```


## Testing

The centralized service registry makes it straight-forward to selectively replace dependencies within your application in tests even if you have many dependencies to handle.

Let's take this simple FastAPI application as an example:

```{literalinclude} ../examples/fastapi/simple_app.py
```

Now if you want to make a request against the `get_user` view, but want the database to raise an error to see if it's properly handled, you can do this:

```{literalinclude} ../examples/fastapi/test_simple_app.py
```

As you can see, we can inspect the decorated lifespan function to get the registry that got injected and you can overwrite it later.

::: {important}
You must overwrite *after* the application has been initialized.
Otherwise the lifespan function overwrites your settings.
:::


## Cleanup

If you initialize the application with a lifespan as shown above, and use the {func}`svcs.fastapi.container` dependency to get your services, everything is cleaned up behind you automatically.


## API Reference

### Application Life Cycle

```{eval-rst}
.. autoclass:: svcs.fastapi.lifespan(lifespan)

   .. seealso:: :ref:`fastapi-init`
```


### Service Acquisition

```{eval-rst}
.. autofunction:: svcs.fastapi.container

.. autoclass:: svcs.fastapi.DepContainer
```
