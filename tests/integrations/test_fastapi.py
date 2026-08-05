# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio
import typing

from contextlib import asynccontextmanager

import pytest

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import svcs

from tests.helpers import CloseMe


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


def test_get_registry():
    """
    get_registry() returns the registry that the lifespan attached to the
    running app.
    """

    @svcs.fastapi.lifespan
    async def lifespan(app: FastAPI, registry: svcs.Registry):
        yield

    app = FastAPI(lifespan=lifespan)

    with TestClient(app):
        assert lifespan.registry is svcs.fastapi.get_registry(app)


def test_get_registry_with_app_and_router_lifespans():
    """
    get_registry() returns the same registry that requests receive when both
    the application and an included router have svcs-aware lifespans.
    """

    @svcs.fastapi.lifespan
    async def app_lifespan(app: FastAPI, registry: svcs.Registry):
        yield

    @svcs.fastapi.lifespan
    async def router_lifespan(app: FastAPI, registry: svcs.Registry):
        yield

    router = APIRouter(lifespan=router_lifespan)

    @router.get("/")
    async def view(registry: svcs.fastapi.DepRegistry):
        return {"uses_app_registry": registry is app_lifespan.registry}

    app = FastAPI(lifespan=app_lifespan)
    app.include_router(router)

    with TestClient(app) as client:
        assert {"uses_app_registry": True} == client.get("/").json()
        assert app_lifespan.registry is svcs.fastapi.get_registry(client)


def test_get_registry_type_hints():
    """
    get_registry()'s annotations can be resolved at runtime.
    """
    hints = typing.get_type_hints(svcs.fastapi.get_registry)

    assert FastAPI | TestClient == hints["app"]
    assert svcs.Registry is hints["return"]


def test_get_registry_no_svcs():
    """
    get_registry() raises LookupError if no registry is attached.
    """
    with pytest.raises(LookupError, match="No svcs registry on app"):
        svcs.fastapi.get_registry(FastAPI())


def test_dep_registry():
    """
    The DepRegistry dependency injects the application's registry.
    """

    @svcs.fastapi.lifespan
    async def lifespan(app: FastAPI, registry: svcs.Registry):
        registry.register_value(int, 42)

        yield

    app = FastAPI(lifespan=lifespan)

    @app.get("/")
    async def view(registry: svcs.fastapi.DepRegistry):
        return {"same": registry is svcs.fastapi.get_registry(app)}

    with TestClient(app) as client:
        assert {"same": True} == client.get("/").json()


def test_get_registry_test_client():
    """
    get_registry() accepts a test client of the app.
    """

    @svcs.fastapi.lifespan
    async def lifespan(app: FastAPI, registry: svcs.Registry):
        yield

    app = FastAPI(lifespan=lifespan)

    with TestClient(app) as client:
        assert lifespan.registry is svcs.fastapi.get_registry(client)


def test_get_registry_test_client_no_svcs():
    """
    get_registry() raises LookupError for a client of an app without svcs.
    """
    with pytest.raises(LookupError, match="No svcs registry on app"):
        svcs.fastapi.get_registry(TestClient(FastAPI()))


def test_get_registry_after_shutdown():
    """
    get_registry() raises LookupError after the app has shut down.
    """

    @svcs.fastapi.lifespan
    async def lifespan(app: FastAPI, registry: svcs.Registry):
        yield

    app = FastAPI(lifespan=lifespan)

    with TestClient(app):
        pass

    with pytest.raises(LookupError, match="No svcs registry on app"):
        svcs.fastapi.get_registry(app)
