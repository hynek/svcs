# AIOHTTP

*svcs*'s [AIOHTTP](https://docs.aiohttp.org/) integration stores the {class}`svcs.Registry` on the {class}`aiohttp.web.Application` object and the {class}`svcs.Container` on the {class}`aiohttp.web.Request` object.


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

### Retrieving Services

```{eval-rst}
.. autofunction:: svcs_from
.. function:: aget

   Same as :meth:`svcs.Container.aget`, but uses the container from *request*.
.. autofunction:: get_pings
```
