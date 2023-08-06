# Glossary

:::{glossary}
service
    A runtime-{term}`resource` that is managed by *svcs*.

    This can be anything you'd like to be loosely coupled from your application code, e.g. a database connection, a web API client, or a cache.

    It's usually also something you need to configure before using and can't just instantiate directly in your business code.

resource
    Same as {term}`service`.
:::
