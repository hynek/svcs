# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio

from dataclasses import dataclass

import pytest


@dataclass
class Service:
    pass


@dataclass
class AnotherService:
    pass


@dataclass
class YetAnotherService:
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

    async def test_aget_works_with_sync_factory(self, registry, container):
        """
        A synchronous factory does not break aget().
        """
        registry.register_factory(Service, Service)

        assert Service() == (await container.aget(Service))

    async def test_aget_works_with_value(self, registry, container):
        """
        A value instead of a factory does not break aget().
        """
        registry.register_value(Service, 42)

        assert 42 == (await container.aget(Service))

    async def test_async_cleanup(self, registry, container):
        """
        Async cleanups are handled by aclose.
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

        assert 1 == len(container.cleanups)
        assert Service() == svc
        assert not cleaned_up

        await container.aclose()

        assert cleaned_up

    @pytest.mark.asyncio()
    async def test_aclose_resilient(self, container, registry, caplog):
        """
        Failing cleanups are logged and ignored. They do not break the
        cleanup process.
        """

        def factory():
            yield 1
            raise Exception

        async def async_factory():
            yield 2
            raise Exception

        cleaned_up = False

        async def factory_no_boom():
            nonlocal cleaned_up

            yield 3

            cleaned_up = True

        registry.register_factory(Service, factory)
        registry.register_factory(AnotherService, async_factory)
        registry.register_factory(YetAnotherService, factory_no_boom)

        assert 1 == container.get(Service)
        assert 2 == await container.aget(AnotherService)
        assert 3 == await container.aget(YetAnotherService)

        assert not cleaned_up

        await container.aclose()

        # Inverse order
        assert "AnotherService" == caplog.records[0].service
        assert "Service" == caplog.records[1].service
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

    async def test_aping(self, registry, container):
        """
        Async and sync pings work.
        """
        apinged = pinged = False

        async def aping(svc):
            await asyncio.sleep(0)
            nonlocal apinged
            apinged = True

        def ping(svc):
            nonlocal pinged
            pinged = True

        registry.register_value(Service, Service(), ping=aping)
        registry.register_value(AnotherService, AnotherService(), ping=ping)

        (ap, p) = container.get_pings()

        assert ap.is_async
        assert not p.is_async

        await ap.aping()
        await p.aping()

        assert pinged
        assert apinged
