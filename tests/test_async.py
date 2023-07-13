import asyncio

from dataclasses import dataclass

import pytest

import svc_reg


@dataclass
class Service:
    pass


@pytest.mark.asyncio()
class TestAsync:
    async def test_async_factory(self):
        """
        A factory can be async.
        """
        reg = svc_reg.Registry()
        container = svc_reg.Container(reg)

        async def factory():
            await asyncio.sleep(0)
            return Service()

        reg.register_factory(Service, factory)

        coro = container.get(Service)

        assert asyncio.iscoroutine(coro)
        assert Service() == await coro

    async def test_async_cleanup(self):
        """
        Async cleanups are handled by acleanup.
        """
        reg = svc_reg.Registry()
        container = svc_reg.Container(reg)

        async def cleanup(svc_):
            await asyncio.sleep(0)
            assert svc is svc_

        reg.register_factory(Service, Service, cleanup=cleanup)

        svc = container.get(Service)

        assert 1 == len(container.async_cleanups)
        assert Service() == svc

        await container.aclose()
