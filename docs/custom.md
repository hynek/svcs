# Custom Integrations

Once you've understood how registries and containers interact (see {doc}`core-concepts` if not), you already know how to write your own integrations!

All you need to do is:

- Create a {class}`~svcs.Registry`s instance and attach it to the application so that the instance lives as long as the application does.

- Ensure that the registry is closed when the application shuts down.
  Either by using the registry as a context manager, or by calling {meth}`~svcs.Registry.close()` or {meth}`~svcs.Registry.aclose()` on your registry instance.

- Give the user an API to access the registry instance such they can register factories on startup.

- On each request, create a {class}`svcs.Container` instance and attach it to the request such that it lives as long as the request.

- Ensure that the container instance is closed when the request is done.

- Give the user an API to access the container instance in views, so they can {meth}`~svcs.Container.get()` their services.

That's it!

If you need inspiration, look at our integrations, like the [one for Flask](https://github.com/hynek/svcs/blob/main/src/svcs/flask.py)!
