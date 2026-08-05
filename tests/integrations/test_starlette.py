# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio
import typing

from contextlib import asynccontextmanager

import pytest

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

import svcs

from tests.fake_factories import async_bool_cm_factory, async_int_factory
from tests.helpers import CloseMe


@pytest.mark.asyncio
@pytest.mark.parametrize("yield_something", [True, False])
@pytest.mark.parametrize("cm", [True, False])
async def test_integration(yield_something, cm):
    """
    Acquiring registered services using a Starlette dependency works.
    """
    close_me_registry = CloseMe()
    close_me_container = CloseMe()

    async def factory():
        await asyncio.sleep(0)
        yield 42
        await asyncio.sleep(0)

        await close_me_container.aclose()

    async def close_registry():
        await close_me_registry.aclose()

    if yield_something:

        async def lifespan(app: Starlette, registry: svcs.Registry):
            registry.register_factory(
                int, factory, on_registry_close=close_registry
            )

            yield {"foo": "bar"}

    else:

        async def lifespan(app: Starlette, registry: svcs.Registry):
            registry.register_factory(
                int, factory, on_registry_close=close_registry
            )

            yield

    if cm:
        lifespan = asynccontextmanager(lifespan)

    async def view(request):
        val = await svcs.starlette.aget(request, int)

        assert (
            val
            == await svcs.starlette.aget_abstract(request, int)
            == await svcs.starlette.svcs_from(request).aget(int)
        )

        return JSONResponse({"val": val})

    app = Starlette(
        lifespan=svcs.starlette.lifespan(lifespan),
        middleware=[Middleware(svcs.starlette.SVCSMiddleware)],
        routes=[Route("/", view)],
    )

    with TestClient(app) as client:
        assert {"val": 42} == client.get("/").json()
        assert close_me_container.is_aclosed

    assert close_me_registry.is_aclosed


async def healthy(request):
    """
    Ping all external services.
    """
    ok = []
    failing = []
    code = 200

    for svc in svcs.starlette.get_pings(request):
        try:
            await svc.aping()
            ok.append(svc.name)
        except Exception as e:  # noqa: PERF203, BLE001
            failing.append({svc.name: repr(e)})
            code = 500

    return JSONResponse(
        content={"ok": ok, "failing": failing}, status_code=code
    )


@pytest.mark.asyncio
async def test_get_pings(registry, container):
    """
    Our get_pings returns registered pings.
    """

    async def aping(_): ...

    async def aboom(_):
        raise ValueError("boom")

    @svcs.starlette.lifespan
    async def lifespan(app: Starlette, registry: svcs.Registry):
        registry.register_factory(int, async_int_factory, ping=aping)
        registry.register_factory(bool, async_bool_cm_factory, ping=aboom)

        yield {"foo": "bar"}

    app = Starlette(
        lifespan=lifespan,
        middleware=[Middleware(svcs.starlette.SVCSMiddleware)],
        routes=[Route("/", healthy)],
    )

    with TestClient(app) as client:
        assert {
            "failing": [
                {"builtins.bool": "ValueError('boom')"},
            ],
            "ok": ["builtins.int"],
        } == client.get("/").json()


def test_get_registry():
    """
    get_registry() returns the registry that the lifespan attached to the
    running app.
    """

    @svcs.starlette.lifespan
    async def lifespan(app: Starlette, registry: svcs.Registry):
        yield

    app = Starlette(lifespan=lifespan)

    with TestClient(app):
        assert lifespan.registry is svcs.starlette.get_registry(app)


def test_get_registry_type_hints():
    """
    get_registry()'s annotations can be resolved at runtime.
    """
    hints = typing.get_type_hints(svcs.starlette.get_registry)

    assert Starlette | TestClient == hints["app"]
    assert svcs.Registry is hints["return"]


def test_get_registry_no_svcs():
    """
    get_registry() raises LookupError if no registry is attached.
    """
    with pytest.raises(LookupError, match="No svcs registry on app"):
        svcs.starlette.get_registry(Starlette())


def test_get_registry_test_client():
    """
    get_registry() accepts a test client of the app.
    """

    @svcs.starlette.lifespan
    async def lifespan(app: Starlette, registry: svcs.Registry):
        yield

    app = Starlette(lifespan=lifespan)

    with TestClient(app) as client:
        assert lifespan.registry is svcs.starlette.get_registry(client)


def test_get_registry_test_client_no_svcs():
    """
    get_registry() raises LookupError for a client of an app without svcs.
    """
    with pytest.raises(LookupError, match="No svcs registry on app"):
        svcs.starlette.get_registry(TestClient(Starlette()))


def test_get_registry_after_shutdown():
    """
    get_registry() raises LookupError after the app has shut down.
    """

    @svcs.starlette.lifespan
    async def lifespan(app: Starlette, registry: svcs.Registry):
        yield

    app = Starlette(lifespan=lifespan)

    with TestClient(app):
        pass

    with pytest.raises(LookupError, match="No svcs registry on app"):
        svcs.starlette.get_registry(app)


def test_get_registry_composed_lifespans():
    """
    With composed svcs lifespans, the first one wins and detaches the
    registry on shutdown.
    """

    @svcs.starlette.lifespan
    async def first(app: Starlette, registry: svcs.Registry):
        yield

    @svcs.starlette.lifespan
    async def second(app: Starlette, registry: svcs.Registry):
        yield

    @asynccontextmanager
    async def combined(app: Starlette):
        async with first(app) as first_state, second(app) as second_state:
            yield {**second_state, **first_state}

    app = Starlette(lifespan=combined)

    with TestClient(app):
        assert first.registry is svcs.starlette.get_registry(app)

    with pytest.raises(LookupError, match="No svcs registry on app"):
        svcs.starlette.get_registry(app)
