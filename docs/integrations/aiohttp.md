# AIOHTTP

*svcs*'s [AIOHTTP](https://docs.aiohttp.org/) integration stores the {class}`svcs.Registry` on the {class}`aiohttp.web.Application` object and the {class}`svcs.Container` on the {class}`aiohttp.web.Request` object.


## Initialization

You add support for *svcs* to your AIOHTTP app by calling {meth}`svcs.aiohttp.init_app` wherever you create your {class}`aiohttp.web.Application` object.


## Service Acquisition

You can get either the {class}`~svcs.Container` using {func}`svcs.aiohttp.svcs_from` and use it as usual, or pluck them directly from the request object using {func}`svcs.aiohttp.aget` that takes a {class}`aiohttp.web.Request` object as its first argument.

(aiohttp-health)=

## Health Checks

As with services, you have the option to either {func}`svcs.aiohttp.svcs_from` on the request or go straight for {func}`svcs.aiohttp.get_pings`.

A health endpoint could look like this:

```{literalinclude} ../examples/aiohttp/health_check.py
```

(aiohttp-cleanup)=

## Cleanup

Acquired services and pings get cleaned up automatically at the end of a request.

If you register *on_registry_close* callbacks, you can use {func}`svcs.aiohttp.aclose_registry` to run them.
{meth}`~svcs.aiohttp.init_app` will automatically add them to the app's {attr}`aiohttp.web.Application.on_cleanup` callbacks.
Therefore, if you shut down your AIOHTTP applications cleanly, you don't have to think about registry cleanup either.


## API Reference

### Application Life Cycle

```{eval-rst}
.. module:: svcs.aiohttp

.. autofunction:: init_app
.. autofunction:: aclose_registry

.. autofunction:: get_registry
```


### Registering Services

```{eval-rst}
.. autofunction:: register_factory
.. autofunction:: register_value
```

### Service Acquisition

```{eval-rst}
.. autofunction:: svcs_from
.. function:: aget(request: aiohttp.web.Request, svc_type1: type, ...)
   :async:

   Same as :meth:`svcs.Container.aget`, but uses the container from *request*.
.. autofunction:: aget_abstract
.. autofunction:: get_pings
```
