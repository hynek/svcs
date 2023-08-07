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
  <a href="https://svcs.hynek.me">
    <img alt="Documentation at ReadTheDocs" src="https://img.shields.io/badge/Docs-Read%20The%20Docs-black">
  </a>
  <a href="LICENSE">
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
> While the code has 100% test and type coverage, and the shipped *Flask* and *Pyramid* integrations have been in production for years, the API details can still change.
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

The goal is to minimize the code for acquiring pluggable resources in your business code to:

```python
def view(request):
    db, api, cache = request.svcs.get(Database, WebAPIClient, Cache)
```

It's ensured that to a type checker like [Mypy](https://mypy-lang.org), `db` has the type `Database`, `api` has the type `WebAPIClient`, and `cache` has the type `Cache`.

<!-- end benefits -->

*svcs* comes with seamless integration for the **Flask** and **Pyramid** web frameworks and has first-class **async** support.

<!-- end index -->
<!-- begin typing -->
While *svcs* has first-class support for static typing, it is **strictly optional** and will always remain so.
*svcs* also doesn't check your types at runtime.

It only forwards the type you have asked for to the type checker.
If you don't use a type checker, that information is simply ignored without any runtime overhead.
<!-- end typing -->

---

Please read the [*Why?*](https://svcs.hynek.me/en/latest/why.html) section of our documentation to learn more.


## Project Links

- [**PyPI**](https://pypi.org/project/svcs/)
- [**Source Code**](https://github.com/hynek/svcs)
- [**Documentation**](https://svcs.hynek.me)
- [**Changelog**](https://github.com/hynek/svcs/blob/main/CHANGELOG.md)

<!-- end pypi -->


## Credits

*svcs* is written by [Hynek Schlawack](https://hynek.me/) and distributed under the terms of the [MIT](https://github.com/hynek/svcs/blob/main/LICENSE) license.

The development is kindly supported by my employer [Variomedia AG](https://www.variomedia.de/) and all my amazing [GitHub Sponsors](https://github.com/sponsors/hynek).

The [Bestagon](https://www.youtube.com/watch?v=thOifuHs6eY) locator logo is made by [Lynn Root](https://www.roguelynn.com), based on an [Font Awesome](https://fontawesome.com) Icon.
*svcs* has started out as a wrapper around [*wired*](https://wired.readthedocs.io/) by [Michael Merickel](https://michael.merickel.org/) and has been heavily influenced by it.
