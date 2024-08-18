# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio

from contextlib import asynccontextmanager

import pytest

import svcs

from tests.helpers import CloseMe


try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except ImportError:
    pytest.skip("FastAPI not installed", allow_module_level=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("yield_something", [True, False])
@pytest.mark.parametrize("cm", [True, False])
async def test_integration(yield_something, cm):
    """
    Acquiring registered services using a FastAPI dependency works.
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

        async def lifespan(app: FastAPI, registry: svcs.Registry):
            registry.register_factory(
                int, factory, on_registry_close=close_registry
            )

            yield {"foo": "bar"}

    else:

        async def lifespan(app: FastAPI, registry: svcs.Registry):
            registry.register_factory(
                int, factory, on_registry_close=close_registry
            )

            yield

    if cm:
        lifespan = asynccontextmanager(lifespan)

    app = FastAPI(lifespan=svcs.fastapi.lifespan(lifespan))

    @app.get("/")
    async def view(services: svcs.fastapi.DepContainer):
        return {"val": await services.aget(int)}

    with TestClient(app) as client:
        assert {"val": 42} == client.get("/").json()
        assert close_me_container.is_aclosed

    assert close_me_registry.is_aclosed
