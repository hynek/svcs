# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT


from unittest.mock import Mock

import pytest

from .ifaces import AnotherService, Service


class TestContainer:
    def test_get_pings_empty(self, container):
        """
        get_pings returns an empty list if there are no pings.
        """
        assert [] == container.get_pings()

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

    def test_contains(self, container):
        """
        If a service is instantiated within a container, `in` returns True,
        False otherwise.
        """
        container.registry.register_value(int, 42)

        assert int not in container

        container.get(int)

        assert int in container

    def test_context_manager(self, container):
        """
        The container is also a context manager that closes on exit.
        """
        closed = False

        def factory():
            yield 42
            nonlocal closed
            closed = True

        container.registry.register_factory(int, factory)

        with container:
            assert 42 == container.get(int)

        assert closed

    @pytest.mark.asyncio()
    async def test_async_context_manager(self, container):
        """
        The container is also an async context manager that acloses on exit.
        """
        closed = False

        async def factory():
            yield 42
            nonlocal closed
            closed = True

        container.registry.register_factory(int, factory)

        async with container:
            assert 42 == await container.aget(int)

        assert closed


class TestServicePing:
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
