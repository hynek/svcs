# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import gc

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

    @pytest.mark.asyncio()
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
