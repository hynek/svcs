import asyncio

from dataclasses import dataclass

import pytest


@dataclass
class Service:
    pass


@pytest.mark.asyncio()
class TestAsync:
    async def test_async_factory(self, registry, container):
        """
        A factory can be async.
        """

        async def factory():
            await asyncio.sleep(0)
            return Service()

        registry.register_factory(Service, factory)

        svc = await container.aget(Service)

        assert isinstance(svc, Service)
        assert svc is (await container.aget(Service))

    async def test_async_cleanup(self, registry, container):
        """
        Async cleanups are handled by acleanup.
        """
        cleaned_up = False

        async def factory():
            nonlocal cleaned_up
            await asyncio.sleep(0)

            yield Service()

            await asyncio.sleep(0)
            cleaned_up = True

        registry.register_factory(Service, factory)

        svc = await container.aget(Service)

        assert 1 == len(container.async_cleanups)
        assert Service() == svc
        assert not cleaned_up

        await container.aclose()

        assert cleaned_up

    async def test_warns_if_generator_does_not_stop_after_cleanup(
        self, registry, container
    ):
        """
        If a generator doesn't stop after cleanup, a warning is emitted.
        """

        async def factory():
            yield Service()
            yield 42

        registry.register_factory(Service, factory)

        await container.aget(Service)

        with pytest.warns(UserWarning) as wi:
            await container.aclose()

        assert (
            "clean up for <RegisteredService("
            "svc_type=tests.test_async.Service, has_ping=False)> "
            "didn't stop iterating" == wi.pop().message.args[0]
        )
