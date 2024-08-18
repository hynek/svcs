# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio

from contextlib import asynccontextmanager

import pytest

import svcs

from tests.fake_factories import async_bool_cm_factory, async_int_factory
from tests.helpers import CloseMe


try:
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient
except ImportError:
    pytest.skip("Starlette not installed", allow_module_level=True)


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
