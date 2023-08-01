# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio
import contextlib
import inspect

from unittest.mock import AsyncMock, Mock

import pytest

import svcs


needs_working_async_mock = pytest.mark.skipif(
    not inspect.iscoroutinefunction(AsyncMock()),
    reason="AsyncMock not working",
)


class Service:
    pass


class AnotherService:
    pass


class YetAnotherService:
    pass


@pytest.fixture(name="rs")
def _rs(svc):
    return svcs.RegisteredService(Service, Service, False, False, None)


@pytest.fixture(name="svc")
def _svc():
    return Service()


class TestIntegration:
    def test_passes_container_bc_name(self, registry, container):
        """
        If the factory takes an argument called `svcs_container`, it is passed
        on instantiation.
        """

        def factory(svcs_container):
            return str(svcs_container.get(int))

        registry.register_value(int, 42)
        registry.register_factory(str, factory)

        assert "42" == container.get(str)

    def test_passes_container_bc_annotation(self, registry, container):
        """
        If the factory takes an argument annotated with svcs.Container, it is
        passed on instantiation.
        """

        def factory(foo: svcs.Container):
            return str(foo.get(int))

        registry.register_value(int, 42)
        registry.register_factory(str, factory)

        assert "42" == container.get(str)


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

    def test_forget_about_nothing_registered(self, container):
        """
        forget_about does nothing if nothing has been registered.
        """
        container.forget_about(Service)

    def test_forget_about_no_cleanup(self, container, rs, svc):
        """
        forget_about removes the registered service from the container.
        """
        container._instantiated[rs.svc_type] = (rs, svc)

        container.forget_about(Service)

        assert {} == container._instantiated
        assert [] == container._on_close

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
        assert not container._instantiated
        assert not container._on_close

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

        assert "tests.test_core.Service" == caplog.records[0].svcs_service_name
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
            "Container clean up for 'tests.test_core.Service' "
            "didn't stop iterating." == wi.pop().message.args[0]
        )


class TestRegisteredService:
    def test_repr(self, rs):
        """
        repr uses the fully-qualified name of a svc type.
        """

        assert (
            "<RegisteredService(svc_type=tests.test_core.Service, "
            "<class 'tests.test_core.Service'>, takes_container=False, "
            "has_ping=False"
            ")>"
        ) == repr(rs)

    def test_name(self, rs):
        """
        The name property deducts the correct class name.
        """

        assert "tests.test_core.Service" == rs.name


class TestServicePing:
    def test_name(self, rs):
        """
        The name property proxies the correct class name.
        """

        assert "tests.test_core.Service" == svcs.ServicePing(None, rs).name

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
        assert not container._instantiated
        assert not container._on_close


class TestRegistry:
    def test_empty_close(self):
        """
        Closing an empty registry does nothing.
        """
        svcs.Registry().close()

        with contextlib.closing(svcs.Registry()):
            ...

    def test_close_closes(self, registry):
        """
        Calling close on Registry runs all on_close callbacks.
        """
        close_1 = Mock()
        close_2 = Mock()

        registry.register_factory(Service, Service, on_registry_close=close_1)
        registry.register_value(
            AnotherService, AnotherService, on_registry_close=close_2
        )

        registry.close()

        assert close_1.called
        assert close_2.called
        assert not registry._services
        assert not registry._on_close

    def test_overwritten_factories_are_not_forgotten(self, registry):
        """
        If a factory is overwritten, it's close callback is still called.
        """
        close_1 = Mock()
        close_2 = Mock()

        registry.register_factory(Service, Service, on_registry_close=close_1)
        registry.register_value(
            Service, AnotherService, on_registry_close=close_2
        )

        registry.close()

        assert close_1.called
        assert close_2.called

    def test_close_warns_about_async(self, registry):
        """
        Calling close raises a warning if there are async cleanups.
        """

        async def hook():
            ...

        registry.register_factory(Service, Service, on_registry_close=hook)

        with pytest.warns(
            UserWarning,
            match="Skipped async cleanup for 'tests.test_core.Service'.",
        ):
            registry.close()

    def test_close_logs_failures(self, registry, caplog):
        """
        Closing failures are logged but ignored.
        """
        registry.register_factory(
            Service, Service, on_registry_close=Mock(side_effect=ValueError())
        )

        with contextlib.closing(registry):
            ...

        assert "tests.test_core.Service" == caplog.records[0].svcs_service_name

    def test_detects_async_factories(self, registry):
        """
        The is_async property of the RegisteredService is True if the factory
        needs to be awaited.
        """

        async def factory():
            return 42

        async def factory_cleanup():
            await asyncio.sleep(0)
            yield str(42)

        registry.register_factory(int, factory)
        registry.register_factory(str, factory_cleanup)

        assert (
            svcs.RegisteredService(int, factory, False, True, None)
            == registry._services[int]
        )
        assert (
            svcs.RegisteredService(str, factory_cleanup, False, True, None)
            == registry._services[str]
        )

    def test_no_false_positive_async(self, registry):
        """
        is_async is False for sync factories.
        """

        def factory():
            return 42

        def factory_cleanup():
            yield "42"

        registry.register_factory(int, factory)
        registry.register_factory(str, factory_cleanup)

        assert (
            svcs.RegisteredService(int, factory, False, False, None)
            == registry._services[int]
        )
        assert (
            svcs.RegisteredService(str, factory_cleanup, False, False, None)
            == registry._services[str]
        )

    @pytest.mark.skipif(
        not hasattr(contextlib, "aclosing"),
        reason="Hasn't contextlib.aclosing()",
    )
    @pytest.mark.asyncio()
    async def test_async_empty_close(self, registry):
        """
        Asynchronously closing an empty registry does nothing.
        """
        await registry.aclose()

        async with contextlib.aclosing(svcs.Registry()):
            ...

    @pytest.mark.asyncio()
    @needs_working_async_mock
    async def test_aclose_mixed(self, registry):
        """
        aclose() closes all services, including async ones.
        """
        sync_close = Mock()
        async_close = AsyncMock()

        registry.register_factory(
            Service, Service, on_registry_close=sync_close
        )
        registry.register_factory(
            AnotherService, AnotherService, on_registry_close=async_close
        )

        await registry.aclose()

        assert sync_close.called

        async_close.assert_awaited_once()

    @pytest.mark.asyncio()
    @needs_working_async_mock
    async def test_aclose_logs_failures(self, registry, caplog):
        """
        Async closing failures are logged but ignored.
        """
        close_mock = AsyncMock(side_effect=ValueError())

        registry.register_factory(
            Service,
            Service,
            on_registry_close=close_mock,
        )

        await registry.aclose()

        close_mock.assert_awaited_once()
        assert "tests.test_core.Service" == caplog.records[0].svcs_service_name


def factory_wrong_annotation(foo: svcs.Registry) -> int:
    return 42


class TestTakesContainer:
    @pytest.mark.parametrize(
        "factory",
        [lambda: None, lambda container: None, factory_wrong_annotation],
    )
    def test_nope(self, factory):
        """
        Functions with different names and annotations are ignored.
        """
        assert not svcs._core._takes_container(factory)

    def test_name(self):
        """
        Return True if the name is `svcs_container`.
        """

        def factory(svcs_container):
            return 42

        assert svcs._core._takes_container(factory)

    def test_annotation(self):
        """
        Return true if the first argument is annotated as `svcs.Container`.
        """

        def factory(foo: svcs.Container):
            return 42

        assert svcs._core._takes_container(factory)

    def test_annotation_str(self):
        """
        Return true if the first argument is annotated as `svcs.Container`
        using a string.
        """

        def factory(bar: "svcs.Container"):
            return 42

        assert svcs._core._takes_container(factory)

    def test_catches_invalid_sigs(self):
        """
        If the factory takes more than one parameter, raise an TypeError.
        """

        def factory(foo, bar):
            return 42

        with pytest.raises(
            TypeError, match="Factories must take 0 or 1 parameters."
        ):
            svcs._core._takes_container(factory)

    def test_call_works(self):
        """
        Does not raise if the factory is a class with __call__.
        """

        class Factory:
            def __call__(self, svcs_container):
                return 42

        assert svcs._core._takes_container(Factory())
