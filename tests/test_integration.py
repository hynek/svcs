# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio

import pytest

import svcs

from .fake_factories import nop
from .ifaces import AnotherService, Service, YetAnotherService


def test_register_factory_get(registry, container):
    """
    register_factory registers a factory and get returns the service.

    The service is cached.
    """
    registry.register_factory(Service, Service)

    svc = container.get(Service)

    assert isinstance(svc, Service)
    assert svc is container.get(Service)


def test_register_value_get(registry, container, svc):
    """
    register_value registers a service object and get returns it.
    """
    registry.register_value(Service, svc)

    assert svc is container.get(Service)
    assert svc is container.get(Service)


def test_get_not_found(container):
    """
    Asking for a service that isn't registered raises a ServiceNotFoundError.
    """
    with pytest.raises(svcs.exceptions.ServiceNotFoundError) as ei:
        container.get(Service)

    assert Service is ei.value.args[0]


def test_passes_container_bc_name(registry, container):
    """
    If the factory takes an argument called `svcs_container`, it is passed on
    instantiation.
    """

    def factory(svcs_container):
        return str(svcs_container.get(int))

    registry.register_value(int, 42)
    registry.register_factory(str, factory)

    assert "42" == container.get(str)


def test_passes_container_bc_annotation(registry, container):
    """
    If the factory takes an argument annotated with svcs.Container, it is
    passed on instantiation.
    """

    def factory(foo: svcs.Container):
        return str(foo.get(int))

    registry.register_value(int, 42)
    registry.register_factory(str, factory)

    assert "42" == container.get(str)


def test_get_pings(registry, container, svc):
    """
    get_pings returns a list of ServicePings.
    """
    registry.register_factory(AnotherService, AnotherService)
    registry.register_value(Service, svc, ping=nop)

    assert [Service] == [ping._rs.svc_type for ping in container.get_pings()]


def test_cleanup_called(registry, container):
    """
    Services that have a cleanup have them called on cleanup.
    """
    cleaned_up = False

    def factory():
        nonlocal cleaned_up
        yield 42
        cleaned_up = True

    registry.register_factory(Service, factory)

    container.get(Service)

    assert not cleaned_up

    container.close()

    assert cleaned_up
    assert not container._instantiated
    assert not container._on_close


def test_close_resilient(container, registry, caplog):
    """
    Failing cleanups are logged and ignored. They do not break the cleanup
    process.
    """

    def factory():
        yield 1
        raise Exception

    cleaned_up = False

    def factory_no_boom():
        nonlocal cleaned_up

        yield 3

        cleaned_up = True

    registry.register_factory(Service, factory)
    registry.register_factory(YetAnotherService, factory_no_boom)

    assert 1 == container.get(Service)
    assert 3 == container.get(YetAnotherService)

    assert not cleaned_up

    container.close()

    assert "tests.ifaces.Service" == caplog.records[0].svcs_service_name
    assert cleaned_up


def test_warns_if_generator_does_not_stop_after_cleanup(registry, container):
    """
    If a generator doesn't stop after cleanup, a warning is emitted.
    """

    def factory():
        yield Service()
        yield 42

    registry.register_factory(Service, factory)

    container.get(Service)

    with pytest.warns(UserWarning) as wi:
        container.close()

    assert (
        "Container clean up for 'tests.ifaces.Service' "
        "didn't stop iterating." == wi.pop().message.args[0]
    )


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

        assert 1 == len(container._on_close)
        assert Service() == svc
        assert not cleaned_up

        await container.aclose()

        assert cleaned_up
        assert not container._instantiated
        assert not container._on_close

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
        assert (
            "tests.ifaces.AnotherService"
            == caplog.records[0].svcs_service_name
        )
        assert "tests.ifaces.Service" == caplog.records[1].svcs_service_name
        assert cleaned_up
        assert not container._instantiated
        assert not container._on_close

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
            "Container clean up for 'tests.ifaces.Service' "
            "didn't stop iterating." == wi.pop().message.args[0]
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
