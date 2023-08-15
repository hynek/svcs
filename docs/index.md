---
hide-toc: true
---

# *svcs*: A Flexible Service Locator

Release **{sub-ref}`release`**  ([What's new?](https://github.com/hynek/svcs/blob/main/CHANGELOG.md))

::: {admonition} ☠️ Not ready yet! ☠️
:class: danger

This project is only public to [gather feedback](https://github.com/hynek/svcs/discussions), and everything can and will change until the project is proclaimed stable.

The code has 100% test and type coverage, and the shipped *Flask* and *Pyramid* integrations have been in production for years, but the API details can still change.
:::

```{include} ../README.md
:start-after: "<!-- begin index -->"
:end-before: "<!-- end index -->"
```

<!-- begin tabbed teaser -->
<!--
; skip: start
-->
::: {tab} AIOHTTP
```python
import svcs

async def view(request):
    db, api, cache = await svcs.aiohttp.aget(request, Database, WebAPI, Cache)

    ...
```
:::
::: {tab} FastAPI
```python
import svcs

@app.get("/")
async def view(services: svcs.fastapi.DepContainer):
    db, api, cache = await services.aget(Database, WebAPI, Cache)

    ...
```
:::
::: {tab} Flask
```python
import svcs

@app.route("/")
def view():
    db, api, cache = svcs.flask.get(Database, WebAPI, Cache)

    ...
```
:::
::: {tab} Pyramid
```python
import svcs

@view_config(route_name="index")
def view(request):
    db, api, cache = svcs.pyramid.get(request, Database, WebAPI, Cache)

    ...
```
:::
<!-- end tabbed teaser -->

```{include} ../README.md
:start-after: "<!-- begin addendum -->"
:end-before: "<!-- end addendum -->"
```

Read on in *{doc}`why`*, if you find that intriguing!

```{toctree}
:hidden:

why
core-concepts
integrations/index
typing-caveats
glossary
```

```{toctree}
:hidden:
:caption: Meta

PyPI <https://pypi.org/project/svcs/>
GitHub <https://github.com/hynek/svcs/>
Changelog <https://github.com/hynek/svcs/blob/main/CHANGELOG.md>
Contributing <https://github.com/hynek/svcs/blob/main/.github/CONTRIBUTING.md>
Security Policy <https://github.com/hynek/svcs/blob/main/.github/SECURITY.md>
Funding <https://hynek.me/say-thanks/>
```


## Credits

```{include} ../README.md
:start-after: "## Credits"
```
