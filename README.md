<!-- begin logo -->
<p align="center">
  <a href="https://github.com/hynek/svcs/">
    <img src="docs/_static/logo_with_name.svg" width="35%" alt="svcs logo showing a hexagon-shaped radar" />
  </a>
</p>

<p align="center">
  <em>A Flexible Service Locator for Python.</em>
</p>

<!-- end logo -->

<p align="center">
  <a href="https://svcs.hynek.me"><img alt="Documentation at ReadTheDocs" src="https://img.shields.io/badge/Docs-Read%20The%20Docs-black"></a>
  <a href="https://www.bestpractices.dev/projects/8115"><img src="https://www.bestpractices.dev/projects/8115/badge"></a>
  <a href="https://pypi.org/project/svcs/"><img alt="PyPI" src="https://img.shields.io/pypi/v/svcs"></a>
   <a href="https://pepy.tech/project/svcs"><img src="https://static.pepy.tech/personalized-badge/svcs?period=month&units=international_system&left_color=grey&right_color=blue&left_text=Downloads%20/%20Month" alt="Downloads per month" /></a>
  <a href="https://pypi.org/project/svcs/"><img alt="PyPI - Supported Python versions" src="https://img.shields.io/pypi/pyversions/svcs.svg"></a>
</p>

---

<!-- begin pypi -->
<!-- begin index -->

*svcs* (pronounced *services*) is a **dependency container** for Python.
It gives you a central place to register factories for types/interfaces and then imperatively acquire instances of those types with **automatic cleanup** and **health checks**.

It's suitable for implementing [Inversion of Control](https://svcs.hynek.me/en/latest/glossary.html#term-Inversion-of-Control) using either **dependency injection** or **service location** while not requiring global state, decorators, or mangling of function signatures.

<!-- begin benefits -->
Benefits:

- Eliminates tons of repetitive **boilerplate** code,
- unifies **acquisition** and **cleanups** of services,
- provides full *static* **type safety** for them,
- simplifies **testing** through **loose coupling**,
- improves *live* **introspection** and **monitoring** with **health checks**.

The goal is to minimize the code for acquiring pluggable services to:

<!-- end index -->
<!-- end benefits -->

<!-- skip: next -->

```python
from svcs.your_framework import svcs_from

def view(request):
    db, api, cache = svcs_from(request).get(Database, WebAPIClient, Cache)
```

... or less!

<!-- begin addendum -->
To a type checker like [Mypy](https://mypy-lang.org), `db` has the type `Database`, `api` has the type `WebAPIClient`, and `cache` has the type `Cache`.
`db`, `api`, and `cache` will be automatically cleaned up when the request ends -- it's context managers all the way down.
<!-- end addendum -->

*svcs* comes with seamless integration for **AIOHTTP**, **FastAPI**, **Flask**, **Pyramid**, and **Starlette**.

<!-- begin typing -->
While *svcs* also has first-class support for static typing, it is **strictly optional** and will always remain so.
*svcs* also doesn't check your types at runtime.
It only forwards the type you have asked for to the type checker.
If you don't use a type checker, that information is ignored without any runtime overhead.
<!-- end typing -->

Read on in [*Why?*](https://svcs.hynek.me/en/latest/why.html) or watch this short video if you're intrigued:

[![Watch the video](https://img.youtube.com/vi/d1elMD9WgpA/maxresdefault.jpg)](https://youtu.be/d1elMD9WgpA)


## Project Links

- [**PyPI**](https://pypi.org/project/svcs/)
- [**GitHub**](https://github.com/hynek/svcs)
- [**Documentation**](https://svcs.hynek.me)
- [**Changelog**](https://github.com/hynek/svcs/blob/main/CHANGELOG.md)
- [**Funding**](https://hynek.me/say-thanks/)
- [**Third-party extensions**](https://github.com/hynek/svcs/wiki/Third%E2%80%90party-Extensions)

<!-- end pypi -->


## Credits

*svcs* is written by [Hynek Schlawack](https://hynek.me/) and distributed under the terms of the [MIT](https://github.com/hynek/svcs/blob/main/LICENSE) license.

The development is kindly supported by my employer [Variomedia AG](https://www.variomedia.de/) and all my fabulous [GitHub Sponsors](https://github.com/sponsors/hynek).

The [Bestagon](https://www.youtube.com/watch?v=thOifuHs6eY) radar logo is made by [Lynn Root](https://www.roguelynn.com), based on an [Font Awesome](https://fontawesome.com) icon.
*svcs* has started out as a wrapper around [*wired*](https://wired.readthedocs.io/) by [Michael Merickel](https://michael.merickel.org/) and has been heavily influenced by it.


## *svcs* for Enterprise

Available as part of the [Tidelift Subscription](https://tidelift.com/?utm_source=lifter&utm_medium=referral&utm_campaign=hynek).

The maintainers of *svcs* and thousands of other packages are working with Tidelift to deliver commercial support and maintenance for the open source packages you use to build your applications.
Save time, reduce risk, and improve code health, while paying the maintainers of the exact packages you use.
