# Custom Integrations

If you've understood how registries and containers interact (see {doc}`core-concepts` if not), you already know how to write your own integrations!

All you need to do is:

- Create a registry and attach it to the application so that the registry lives as long as the application does.

- Ensure that the registry is closed when the application shuts down.

- Give the user an API to access the registry and register factories on startup.

- On each request, create a container and attach it to the request such that it lives as long as the request.

- Ensure that the container is closed when the request is done.

- Give the user an API to access the container in views such that they can get their services.

If you need inspiration, look at our integrations, like the [one for Flask](https://github.com/hynek/svcs/blob/main/src/svcs/flask.py)!
