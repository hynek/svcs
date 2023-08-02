# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import contextlib
import inspect

from unittest.mock import AsyncMock, Mock

import pytest

import svcs

from .fake_factories import (
    async_int_factory,
    async_str_cleanup_factory,
    int_factory,
    str_cleanup_factory,
)
from .ifaces import AnotherService, Service


needs_working_async_mock = pytest.mark.skipif(
    not inspect.iscoroutinefunction(AsyncMock()),
    reason="AsyncMock not working",
)


class TestRegistry:
    def test_repr_empty(self, registry):
        """
        repr of an empty registry says 0 registered services.
        """
        assert "<svcs.Registry(num_services=0)>" == repr(registry)

    def test_repr_counts(self, registry):
        """
        repr counts 2 registered services as 2.
        """
        registry.register_factory(Service, Service)
        registry.register_factory(AnotherService, AnotherService)

        assert "<svcs.Registry(num_services=2)>" == repr(registry)

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
            match="Skipped async cleanup for 'tests.ifaces.Service'.",
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

        assert "tests.ifaces.Service" == caplog.records[0].svcs_service_name

    def test_detects_async_factories(self, registry):
        """
        The is_async property of the RegisteredService is True if the factory
        needs to be awaited.
        """

        registry.register_factory(int, async_int_factory)
        registry.register_factory(str, async_str_cleanup_factory)

        assert (
            svcs.RegisteredService(int, async_int_factory, False, True, None)
            == registry._services[int]
        )
        assert (
            svcs.RegisteredService(
                str, async_str_cleanup_factory, False, True, None
            )
            == registry._services[str]
        )

    def test_no_false_positive_async(self, registry):
        """
        is_async is False for sync factories.
        """
        registry.register_factory(int, int_factory)
        registry.register_factory(str, str_cleanup_factory)

        assert (
            svcs.RegisteredService(int, int_factory, False, False, None)
            == registry._services[int]
        )
        assert (
            svcs.RegisteredService(
                str, str_cleanup_factory, False, False, None
            )
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
        assert "tests.ifaces.Service" == caplog.records[0].svcs_service_name


class TestRegisteredService:
    def test_repr(self, rs):
        """
        repr uses the fully-qualified name of a svc type.
        """

        assert (
            "<RegisteredService(svc_type=tests.ifaces.Service, "
            "<class 'tests.ifaces.Service'>, takes_container=False, "
            "has_ping=False"
            ")>"
        ) == repr(rs)

    def test_name(self, rs):
        """
        The name property deducts the correct class name.
        """

        assert "tests.ifaces.Service" == rs.name


def wrong_annotation(foo: svcs.Registry) -> int:
    ...


def no_args():
    ...


def diff_name():
    ...


class TestTakesContainer:
    @pytest.mark.parametrize(
        "factory",
        [no_args, diff_name, wrong_annotation],
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
            ...

        assert svcs._core._takes_container(factory)

    def test_annotation(self):
        """
        Return true if the first argument is annotated as `svcs.Container`.
        """

        def factory(foo: svcs.Container):
            ...

        assert svcs._core._takes_container(factory)

    def test_annotation_str(self):
        """
        Return true if the first argument is annotated as `svcs.Container`
        using a string.
        """

        def factory(bar: "svcs.Container"):
            ...

        assert svcs._core._takes_container(factory)

    def test_catches_invalid_sigs(self):
        """
        If the factory takes more than one parameter, raise an TypeError.
        """

        def factory(foo, bar):
            ...

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
                ...

        assert svcs._core._takes_container(Factory())
