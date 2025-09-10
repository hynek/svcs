# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import gc

from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from unittest.mock import Mock

import pytest

import svcs

from .fake_factories import (
    async_bool_cm_factory,
    async_str_gen_factory,
    bool_cm_factory,
    str_gen_factory,
)
from .ifaces import AnotherService, Service, YetAnotherService


class TestContainer:
    def test_get_pings_empty(self, container):
        """
        get_pings returns an empty list if there are no pings.
        """
        assert [] == container.get_pings()

    @pytest.mark.asyncio
    async def test_repr(self, registry, container):
        """
        The repr counts correctly.
        """
        registry.register_factory(Service, str_gen_factory)
        registry.register_factory(bool, bool_cm_factory)
        registry.register_factory(AnotherService, async_str_gen_factory)
        registry.register_factory(YetAnotherService, async_bool_cm_factory)

        container.get(Service)
        container.get(bool)
        await container.aget(AnotherService)
        await container.aget(YetAnotherService)

        assert "<Container(instantiated=4, cleanups=4)>" == repr(container)

        await container.aclose()

    def test_contains(self, container):
        """
        If a service is instantiated within a container, `in` returns True,
        False otherwise.
        """
        container.registry.register_value(int, 42)

        assert int not in container

        container.get(int)

        assert int in container

    def test_context_manager(self, container, close_me):
        """
        The container is also a context manager that closes on exit.
        """

        def factory():
            yield 42
            close_me.close()

        container.registry.register_factory(int, factory)

        with container:
            assert 42 == container.get(int)

        assert close_me.is_closed

    @pytest.mark.asyncio
    async def test_async_context_manager(self, container, close_me):
        """
        The container is also an async context manager that acloses on exit.
        """

        async def factory():
            yield 42
            await close_me.aclose()

        container.registry.register_factory(int, factory)

        async with container:
            assert 42 == await container.aget(int)

        assert close_me.is_aclosed

    @pytest.mark.asyncio
    async def test_async_context_manager_sync_factory(self, container):
        """
        If an async factory returns an context manager, it's entered.
        """
        entered = left = False

        @contextmanager
        def cm():
            nonlocal entered, left
            entered = True
            yield 42
            left = True

        async def factory(svcs_container):
            return cm()

        container.registry.register_factory(int, factory)

        async with container:
            assert 42 == await container.aget(int)

        assert entered
        assert left

    @pytest.mark.asyncio
    async def test_async_context_manager_async_factory(self, container):
        """
        If an async factory returns an async context manager, it's entered.
        """
        entered = left = False

        @asynccontextmanager
        async def cm():
            nonlocal entered, left
            entered = True
            yield 42
            left = True

        async def factory(svcs_container):
            return cm()

        container.registry.register_factory(int, factory)

        async with container:
            assert 42 == await container.aget(int)

        assert entered
        assert left

    def test_gc_warning(self, recwarn, registry):
        """
        If a container is gc'ed with pending cleanups, a warning is raised.
        """

        def scope():
            container = svcs.Container(registry)
            registry.register_factory(str, str_gen_factory)
            container.get(str)

        scope()

        gc.collect()

        assert (
            "Container was garbage-collected with pending cleanups.",
        ) == recwarn.list[0].message.args

    @pytest.mark.asyncio
    async def test_aget_enters_sync_contextmanagers(self, container):
        """
        aget enters (and exits) synchronous context managers.
        """
        is_closed = False

        def factory():
            yield 42

            nonlocal is_closed
            is_closed = True

        container.registry.register_factory(int, factory)

        async with container:
            assert 42 == await container.aget(int)

        assert is_closed

    def test_suppress_context_exit_suppress(self, container, close_me):
        """
        By default, if an error in the synchronous container context is raised,
        it's suppressed and the factory's clean up is ran as if nothing
        happened.
        """

        def factory():
            yield 42
            close_me.close()

        container.registry.register_factory(int, factory)

        with pytest.raises(ValueError), container:
            assert 42 == container.get(int)
            raise ValueError

        assert close_me.is_closed

    def test_suppress_context_exit_no_suppress_handled(
        self, container, close_me, caplog
    ):
        """
        If suppress_context_exit is False, the error is propagated into the
        factory. The factory can still handle the error and clean up. The error
        bubbles out of the container context.
        """
        captured = False

        def factory():
            nonlocal captured

            try:
                yield 42
            except ValueError:
                captured = True

            close_me.close()

        container.registry.register_factory(
            int, factory, suppress_context_exit=False
        )

        with pytest.raises(ValueError), container:
            assert 42 == container.get(int)
            raise ValueError

        assert close_me.is_closed
        assert captured

    @pytest.mark.asyncio
    async def test_async_suppress_context_exit_async_factory_suppress(
        self, container, close_me
    ):
        """
        By default, if an error in the async container context is raised, it's
        suppressed and the factory's clean up is ran as if nothing happened
        """

        async def factory():
            yield 42
            await close_me.aclose()

        container.registry.register_factory(int, factory)

        with pytest.raises(ValueError):
            async with container:
                assert 42 == await container.aget(int)
                raise ValueError

        assert close_me.is_aclosed

    @pytest.mark.asyncio
    async def test_async_suppress_context_exit_async_factory_no_suppress(
        self, container, close_me, caplog
    ):
        """
        If suppress_context_exit is False, the error is propagated into the
        factory. The factory can still handle the error and clean up. The error
        bubbles out of the container context.
        """
        captured = False

        async def factory():
            nonlocal captured

            try:
                yield 42
            except ValueError:
                captured = True

            await close_me.aclose()

        container.registry.register_factory(
            int, factory, suppress_context_exit=False
        )

        with pytest.raises(ValueError):
            async with container:
                assert 42 == await container.aget(int)
                raise ValueError

        assert close_me.is_aclosed
        assert captured

    @pytest.mark.asyncio
    async def test_async_suppress_context_exit_sync_factory_no_suppress(
        self, container, close_me, caplog
    ):
        """
        If suppress_context_exit is False, the error is propagated into the
        factory. The factory can still handle the error and clean up. The error
        bubbles out of the container context.
        """

        def factory():
            yield 42
            pytest.fail("Exception wasn't propagated.")

        container.registry.register_factory(
            int, factory, suppress_context_exit=False
        )

        with pytest.raises(ValueError):
            async with container:
                assert 42 == await container.aget(int)
                raise ValueError


class TestServicePing:
    @pytest.fixture
    def make_ping_stub(self) -> Callable[[], Mock]:
        return lambda: Mock(spec_set=["__call__"])

    def test_ping(self, registry, container, close_me, make_ping_stub):
        """
        Calling ping instantiates the service using its factory, appends it to
        the cleanup list, and calls the service's ping method.
        """

        def factory():
            yield Service()
            close_me.close()

        ping = make_ping_stub()
        registry.register_factory(Service, factory, ping=ping)

        (svc_ping,) = container.get_pings()

        svc_ping.ping()

        ping.assert_called_once()

        assert not close_me.is_closed

        container.close()

        assert close_me.is_closed
        assert not container._instantiated
        assert not container._on_close

    def test_local_pings_are_retrieved(self, container, make_ping_stub):
        """
        Registering a local factory with a ping defined makes it possible to
        invoke a ping for that service.
        """
        service_ping = make_ping_stub()
        container.register_local_factory(Service, Service, ping=service_ping)

        (svc_ping,) = container.get_pings()
        svc_ping.ping()

        service_ping.assert_called_once()

    def test_local_pings_override_global_pings(
        self, registry, container, make_ping_stub
    ):
        """
        If a local factory overwrites an existing, global one, and the local
        factory has a ping defined, the local ping isused.
        """
        service_ping, local_service_ping = make_ping_stub(), make_ping_stub()
        registry.register_factory(Service, Service, ping=service_ping)
        container.register_local_factory(
            Service,
            Service,
            ping=local_service_ping,
        )

        (svc_ping,) = container.get_pings()
        svc_ping.ping()

        service_ping.assert_not_called()
        local_service_ping.assert_called_once()

    def test_local_services_without_pings_discard_global_pings(
        self, registry, container, make_ping_stub
    ):
        """
        If a local factory overwrites an existing, global one, but the local
        factory does not have a ping defined, the global ping is not returned
        either.
        """
        registry.register_factory(Service, Service, ping=make_ping_stub())
        container.register_local_factory(Service, Service, ping=None)

        assert not container.get_pings()
