---
hide-toc: true
---

# *svcs*: A Flexible Service Locator

Release **{sub-ref}`release`**  ([What's new?](https://github.com/hynek/svcs/blob/main/CHANGELOG.md))


```{include} ../README.md
:start-after: "<!-- begin index -->"
:end-before: "<!-- end index -->"
```

<!-- begin tabbed teaser -->
<!--
; skip: start
-->
:::: {tab-set}
::: {tab-item} AIOHTTP
```python
import svcs

async def view(request):
    db, api, cache = await svcs.aiohttp.aget(request, Database, WebAPIClient, Cache)

    ...
```
:::
::: {tab-item} FastAPI
```python
import svcs

@app.get("/")
async def view(services: svcs.fastapi.DepContainer):
    db, api, cache = await services.aget(Database, WebAPIClient, Cache)

    ...
```
:::
::: {tab-item} Flask
```python
import svcs

@app.route("/")
def view():
    db, api, cache = svcs.flask.get(Database, WebAPIClient, Cache)

    ...
```
:::
::: {tab-item} Pyramid
```python
import svcs

@view_config(route_name="index")
def view(request):
    db, api, cache = svcs.pyramid.get(request, Database, WebAPIClient, Cache)

    ...
```
:::
::: {tab-item} Starlette
```python
import svcs

async def view(request):
    db, api, cache = await svcs.starlette.aget(request, Database, WebAPIClient, Cache)

    ...
```
:::

::::
<!-- end tabbed teaser -->

```{include} ../README.md
:start-after: "<!-- begin addendum -->"
:end-before: "<!-- end addendum -->"
```

Read on in *{doc}`why`* if you're intrigued!

```{toctree}
:hidden:

why
core-concepts
integrations/index
typing-caveats
glossary
credits
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
