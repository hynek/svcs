# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio

from contextlib import asynccontextmanager

import pytest

import svcs


try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except ImportError:
    pytest.skip("FastAPI not installed", allow_module_level=True)


@pytest.mark.asyncio()
@pytest.mark.parametrize("yield_something", [True, False])
@pytest.mark.parametrize("cm", [True, False])
async def test_integration(yield_something, cm):
    """
    Acquiring registered services using a FastAPI dependency works.
    """
    registry_closed = closed = False

    async def factory():
        await asyncio.sleep(0)
        yield 42
        await asyncio.sleep(0)

        nonlocal closed
        closed = True

    async def close_registry():
        nonlocal registry_closed
        registry_closed = True

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
        assert closed

    assert registry_closed
