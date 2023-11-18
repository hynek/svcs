# Typing Caveats

## Abstract Classes and PEP 544

If you try to `get()` an abstract class like an `Protocol` or an *abstract base class* you'll get a Mypy error like this:

```text
error: Only concrete class can be given where "type[P]" is expected  [type-abstract]
```

Unfortunately, it's [impossible](https://github.com/python/mypy/issues/4717) to type-hint `type[P]` when `P` is abstract because it's forbidden by {pep}`544`.

As a stopgap, until we get something better in Python typing, *svcs* comes with `Container.get_abstract()` and `Container.aget_abstract()` that are type-hinted to return {obj}`~typing.Any`.
Since `Any` disables any kind of type-checking, you have to use it like this:

% skip: start

```python
ac: SomeAbstractClass = container.get_abstract(SomeAbstractClass)
```

You can also create bespoke wrappers for your services:

```python
def get_connection() -> Connection:
    return svcs.flask.get_abstract(Connection)
```

Finally, you can disable this error by adding the following line to your Mypy configuration:

```toml
disable_error_code = ["type-abstract"]
```

... or by calling Mypy with the `--disable-error-code=type-abstract` argument.


## Multiple Services

Another caveat is that it's necessary to define multiple return values for `get()` for every single arity.
We've done it for up to **ten service types** which should be plenty.
