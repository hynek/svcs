# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT


from unittest.mock import Mock

import pytest

import svcs

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


class TestServicePing:
    def test_name(self, rs):
        """
        The name property proxies the correct class name.
        """

        assert "tests.ifaces.Service" == svcs.ServicePing(None, rs).name

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
