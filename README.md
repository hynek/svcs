<!-- begin logo -->
<p align="center">
  <a href="https://github.com/hynek/svcs/">
    <img src="docs/_static/logo_with_name.svg" width="35%" alt="svcs logo showing a radar" />
  </a>
</p>

<p align="center">
  <em>A Lightweight Service Locator for Python.</em>
</p>

<!-- end logo -->

<p align="center">
  <img alt="PyPI - Status" src="https://img.shields.io/pypi/status/svcs">
  <a href="./LICENSE">
    <img alt="PyPI - License" src="https://img.shields.io/pypi/l/svcs">
  </a>
  <a href="https://pypi.org/project/svcs/">
    <img alt="PyPI" src="https://img.shields.io/pypi/v/svcs">
  </a>
  <a href="https://pypi.org/project/svcs/">
    <img alt="PyPI - Supported Python versions" src="https://img.shields.io/pypi/pyversions/svcs.svg">
  </a>
</p>

---

<!-- begin pypi -->

> [!WARNING]
> ☠️ Not ready yet! ☠️
>
> This project is only public to [gather feedback](https://github.com/hynek/svcs/discussions), and everything can and will change until the project is proclaimed stable.
>
> The code has 100% test and type coverage, and the [**Flask** integration](#flask) is already in production, but API details can still change.
>
> At this point, it's unclear whether this project will become a "proper Hynek project".
> I will keep using it for my work projects, but whether this will grow beyond my personal needs depends on community interest.

<!-- begin index -->

*svcs* (pronounced *services*) is a [**service locator**](https://en.wikipedia.org/wiki/Service_locator_pattern) for Python.
It gives you a central place to register factories for types/interfaces and then imperatively request instances of those types with **automatic cleanup** and **health checks**.

<!-- begin benefits -->
Benefits:

- Eliminates tons of repetitive **boilerplate** code,
- unifies **acquisition** and **cleanups** of resources,
- provides full *static* **type safety** for them,
- simplifies **testing** through **loose coupling**,
- and allows for easy **health checks** across *all* resources.

The goal is to minimize your business code to:

```python
def view(request):
    db = request.svcs.get(Database)
    api = request.svcs.get(WebAPIClient)
```

To the type checker (e.g. [Mypy](https://mypy-lang.org)), `db` has the type `Database` and `api` has the type `WebAPIClient` and verifies your code as such.

You can also ask for multiple services at once with the same typing benefits:

```python
def view(request):
    db, api = request.svcs.get(Database, WebAPIClient)
```

Or, if you don't shy away from some global state and your web framework supports it, even:

```python
def view():
    db, api = svcs.flask.get(Database, WebAPIClient)
```

<!-- end benefits -->
<!-- end index -->

---

Please read the [*Why?*](https://svcs.hynek.me/) section of our documentation to learn more.


## Project Information

- [**PyPI**](https://pypi.org/project/svcs/)
- [**Source Code**](https://github.com/hynek/svcs)
- [**Documentation**](https://svcs.hynek.me)
- [**Changelog**](https://github.com/hynek/svcs/blob/main/CHANGELOG.md)

<!-- end pypi -->


## Credits

*svcs* is written by [Hynek Schlawack](https://hynek.me/) and distributed under the terms of the [MIT](https://github.com/hynek/svcs/blob/main/LICENSE) license.

The development is kindly supported by my employer [Variomedia AG](https://www.variomedia.de/) and all my amazing [GitHub Sponsors](https://github.com/sponsors/hynek).

The [Bestagon](https://www.youtube.com/watch?v=thOifuHs6eY) locator logo is made by [Lynn Root](https://www.roguelynn.com), based on an [Font Awesome](https://fontawesome.com) Icon.
