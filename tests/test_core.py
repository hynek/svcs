# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio

from unittest.mock import Mock

import pytest

import svcs


class Service:
    pass


class AnotherService:
    pass


class YetAnotherService:
    pass


@pytest.fixture(name="rs")
def _rs(svc):
    return svcs.RegisteredService(Service, Service, None)


@pytest.fixture(name="svc")
def _svc():
    return Service()


class TestContainer:
    def test_register_factory_get(self, registry, container):
        """
        register_factory registers a factory and get returns the service.

        The service is cached.
        """
        registry.register_factory(Service, Service)

        svc = container.get(Service)

        assert isinstance(svc, Service)
        assert svc is container.get(Service)

    def test_register_value_get(self, registry, container, svc):
        """
        register_value registers a service object and get returns it.
        """
        registry.register_value(Service, svc)

        assert svc is container.get(Service)
        assert svc is container.get(Service)

    def test_get_not_found(self, container):
        """
        Asking for a service that isn't registered raises a ServiceNotFoundError.
        """
        with pytest.raises(svcs.exceptions.ServiceNotFoundError) as ei:
            container.get(Service)

        assert Service is ei.value.args[0]

    def test_get_pings_empty(self, container):
        """
        get_pings returns an empty list if there are no pings.
        """
        assert [] == container.get_pings()

    def test_get_pings(self, registry, container, svc):
        """
        get_pings returns a list of ServicePings.
        """
        registry.register_factory(AnotherService, AnotherService)
        registry.register_value(Service, svc, ping=lambda _: None)

        assert [Service] == [
            ping._rs.svc_type for ping in container.get_pings()
        ]

    def test_forget_service_type_nothing_registered(self, container):
        """
        forget_service_type does nothing if nothing has been registered.
        """
        container.forget_service_type(Service)

    def test_forget_service_type_no_cleanup(self, container, rs, svc):
        """
        forget_service_type removes the registered service from the container.
        """
        container.instantiated[rs.svc_type] = (rs, svc)

        container.forget_service_type(Service)

        assert {} == container.instantiated
        assert [] == container.cleanups

    @pytest.mark.asyncio()
    async def test_repr(self, registry, container):
        """
        The repr counts correctly.
        """

        def factory():
            yield 42

        async def async_factory():
            yield 42

        registry.register_factory(Service, factory)
        registry.register_factory(AnotherService, async_factory)

        container.get(Service)
        await container.aget(AnotherService)

        assert "<Container(instantiated=2, cleanups=2)>" == repr(container)

    def test_cleanup_called(self, registry, container):
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

    def test_close_resilient(self, container, registry, caplog):
        """
        Failing cleanups are logged and ignored. They do not break the
        cleanup process.
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

        assert "Service" == caplog.records[0].service
        assert cleaned_up

    def test_warns_if_generator_does_not_stop_after_cleanup(
        self, registry, container
    ):
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
            "clean up for <RegisteredService("
            "svc_type=tests.test_core.Service, has_ping=False)> "
            "didn't stop iterating" == wi.pop().message.args[0]
        )


class TestRegisteredService:
    def test_repr(self, rs):
        """
        repr uses the fully-qualified name of a svc type.
        """

        assert (
            "<RegisteredService(svc_type=tests.test_core.Service, has_ping=False)>"
        ) == repr(rs)

    def test_name(self, rs):
        """
        The name property deducts the correct class name.
        """

        assert "Service" == rs.name

    def test_is_async_yep(self):
        """
        The is_async property returns True if the factory needs to be awaited.
        """

        async def factory():
            return 42

        async def factory_cleanup():
            await asyncio.sleep(0)
            yield 42

        assert svcs.RegisteredService(object, factory, None).is_async
        assert svcs.RegisteredService(object, factory_cleanup, None).is_async

    def test_is_async_nope(self):
        """
        is_async is False for sync factories.
        """

        def factory():
            return 42

        def factory_cleanup():
            yield 42

        assert not svcs.RegisteredService(object, factory, None).is_async
        assert not svcs.RegisteredService(
            object, factory_cleanup, None
        ).is_async


class TestServicePing:
    def test_name(self, rs):
        """
        The name property proxies the correct class name.
        """

        assert "Service" == svcs.ServicePing(None, rs).name

    def test_ping(self, registry, container):
        """
        Calling ping instantiates the service using its factory, appends it to
        the cleanup list, and calls the service's ping method.
        """

        cleaned_up = False

        def factory():
            nonlocal cleaned_up
            yield Service()
            cleaned_up = True

        ping = Mock(spec_set=["__call__"])
        registry.register_factory(Service, factory, ping=ping)

        (svc_ping,) = container.get_pings()

        svc_ping.ping()

        ping.assert_called_once()

        assert not cleaned_up

        container.close()

        assert cleaned_up
