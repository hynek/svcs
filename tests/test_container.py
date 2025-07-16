# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import gc

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
        The default behaviour, even if exception is raised, the factory is cleaned up.
        """

        def factory():
            yield 42
            close_me.close()

        container.registry.register_factory(
            int, factory, suppress_context_exit=True
        )

        with pytest.raises(ValueError), container:  # noqa: PT012
            assert 42 == container.get(int)
            raise ValueError

        assert close_me.is_closed

    def test_suppress_context_exit_no_suppress(self, container, close_me):
        """
        Disabled suppress_context_exit, so the factory is not cleaned up. Exception stack is passed through.
        """

        def factory():
            yield 42
            close_me.close()  # pragma: no cover

        container.registry.register_factory(
            int, factory, suppress_context_exit=False
        )

        with pytest.raises(ValueError), container:  # noqa: PT012
            assert 42 == container.get(int)
            raise ValueError

        assert not close_me.is_closed

    def test_suppress_context_exit_no_suppress_handled(
        self, container, close_me, caplog
    ):
        """
        Disabled suppress_context_exit, so the factory is not cleaned up. Exception stack is passed through and handled in the factory.
        """

        capture_log = Mock()

        def factory():
            try:
                yield 42
            except ValueError:
                capture_log("Exception handled in factory")
            finally:
                close_me.close()

        container.registry.register_factory(
            int, factory, suppress_context_exit=False
        )

        with pytest.raises(ValueError), container:  # noqa: PT012
            assert 42 == container.get(int)
            raise ValueError

        assert close_me.is_closed
        capture_log.assert_called_once_with("Exception handled in factory")

    @pytest.mark.asyncio
    async def test_async_suppress_context_exit_async_factory_suppress(
        self, container, close_me, caplog
    ):
        """
        The default behaviour, even if exception is raised, the factory is cleaned up. Async factory.
        """

        async def factory():
            yield 42
            await close_me.aclose()

        container.registry.register_factory(
            int, factory, suppress_context_exit=True
        )

        with pytest.raises(ValueError):  # noqa: PT012
            async with container:
                assert 42 == await container.aget(int)
                raise ValueError

        assert close_me.is_aclosed

    @pytest.mark.asyncio
    async def test_async_suppress_context_exit_async_factory_no_suppress(
        self, container, close_me, caplog
    ):
        """
        Disabled suppress_context_exit, so the factory is not cleaned up. Exception stack is passed through. Async factory.
        """

        async def factory():
            yield 42
            await close_me.aclose()  # pragma: no cover

        container.registry.register_factory(
            int, factory, suppress_context_exit=False
        )

        with pytest.raises(ValueError):  # noqa: PT012
            async with container:
                assert 42 == await container.aget(int)
                raise ValueError

        assert not close_me.is_aclosed

    @pytest.mark.asyncio
    async def test_async_suppress_context_exit_sync_factory_no_suppress(
        self, container, close_me, caplog
    ):
        """
        Disabled suppress_context_exit, so the factory is not cleaned up. Exception stack is passed through. Sync factory.
        """

        def factory():
            yield 42
            close_me.close()  # pragma: no cover

        container.registry.register_factory(
            int, factory, suppress_context_exit=False
        )

        with pytest.raises(ValueError):  # noqa: PT012
            async with container:
                assert 42 == await container.aget(int)
                raise ValueError

        assert not close_me.is_closed


class TestServicePing:
    def test_ping(self, registry, container, close_me):
        """
        Calling ping instantiates the service using its factory, appends it to
        the cleanup list, and calls the service's ping method.
        """

        def factory():
            yield Service()
            close_me.close()

        ping = Mock(spec_set=["__call__"])
        registry.register_factory(Service, factory, ping=ping)

        (svc_ping,) = container.get_pings()

        svc_ping.ping()

        ping.assert_called_once()

        assert not close_me.is_closed

        container.close()

        assert close_me.is_closed
        assert not container._instantiated
        assert not container._on_close
