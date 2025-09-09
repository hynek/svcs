# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio
import re

from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    asynccontextmanager,
    contextmanager,
)
from typing import NewType

import pytest

import svcs

from .fake_factories import (
    async_bool_cm_factory,
    async_int_factory,
    async_str_gen_factory,
)
from .helpers import Annotated, CloseMe, nop
from .ifaces import AnotherService, Interface, Service, YetAnotherService


def test_register_factory_get(registry, container):
    """
    register_factory registers a factory and get returns the service.

    The service is cached.
    """
    registry.register_factory(Service, Service)

    svc = container.get(Service)

    assert isinstance(svc, Service)
    assert svc is container.get(Service)


def test_register_factory_get_abstract(registry, container):
    """
    register_factory registers a factory and get_abstract returns the service.

    The service is cached.
    """
    registry.register_factory(Interface, Service)

    svc = container.get_abstract(Interface)

    assert isinstance(svc, Interface)
    assert svc is container.get(Interface)


def test_register_value_multiple(registry, container):
    """
    register_value registers a service object and get returns as many values as
    are requeste.
    """
    registry.register_value(Service, 1)
    registry.register_value(AnotherService, 2)

    assert [1, 2] == container.get(Service, AnotherService)
    assert [1, 2] == container.get(Service, AnotherService)


S1 = Annotated[Interface, "s1"]
S2 = NewType("S2", Interface)


def test_get_annotated_multiple(registry, container):
    """
    It's possible to register multiple factories for the same type using
    Annotated TypeAliases.
    """
    registry.register_factory(S1, Service)
    registry.register_factory(S2, AnotherService)

    assert isinstance(container.get(S1), Service)
    assert isinstance(container.get(S2), AnotherService)


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


def test_get_enter_false(registry, container):
    """
    If the factory is registered with enter=False and returns a context
    manager, it is not entered on instantiation.
    """
    entered = False

    @contextmanager
    def factory():
        nonlocal entered
        entered = True
        yield 42

    registry.register_factory(Service, factory, enter=False)

    cm = container.get(Service)

    assert not entered
    assert isinstance(cm, AbstractContextManager)

    with cm as i:
        assert 42 == i

    assert entered


def test_get_pings(registry, container, svc):
    """
    get_pings returns a list of ServicePings.
    """
    registry.register_factory(AnotherService, AnotherService)
    registry.register_value(Service, svc, ping=nop)

    assert [Service] == [ping._svc_type for ping in container.get_pings()]


def test_cleanup_called(registry, container, close_me):
    """
    Services that have a cleanup have them called on cleanup.
    """

    def factory():
        yield 42
        close_me.close()

    registry.register_factory(Service, factory)

    container.get(Service)

    assert not close_me.is_closed

    container.close()

    assert close_me.is_closed
    assert not container._instantiated
    assert not container._on_close


def test_close_resilient(container, registry, caplog, close_me):
    """
    Failing cleanups are logged and ignored. They do not break the cleanup
    process.
    """

    def factory():
        yield 1
        raise Exception

    def factory_no_boom():
        yield 3

        close_me.close()

    registry.register_factory(Service, factory)
    registry.register_factory(YetAnotherService, factory_no_boom)

    assert 1 == container.get(Service)
    assert 3 == container.get(YetAnotherService)

    assert not close_me.is_closed

    container.close()

    assert "tests.ifaces.Service" == caplog.records[0].svcs_service_name
    assert close_me.is_closed


def test_none_is_a_valid_factory_result(registry, container):
    """
    None is a valid factory result and is cached as such.
    """

    i = 0

    def factory():
        nonlocal i
        i += 1
        yield None

    registry.register_factory(Service, factory)

    assert None is container.get(Service)
    assert None is container.get(Service)
    assert 1 == i

    container.close()


@pytest.mark.parametrize(
    "factory",
    [
        async_int_factory,
        async_str_gen_factory,
        async_bool_cm_factory,
    ],
)
def test_get_on_async_factory_raises_type_error(
    registry, container, factory, recwarn
):
    """
    get() on an async factory raises a TypeError.
    """

    registry.register_factory(Service, factory)

    with pytest.raises(
        TypeError, match=re.escape("Use `aget()` for async factories.")
    ):
        container.get(Service)

    if recwarn.list:
        assert (
            "coroutine 'async_int_factory' was never awaited",
        ) == recwarn.pop().message.args


def test_local_value_overrides_global_value(registry, container):
    """
    If a container registers a local value, it takes precedence of the global
    registry. The local registry is created lazily and closed when the
    container is closed.
    """
    registry.register_value(int, 1)

    assert container._lazy_local_registry is None

    cm = CloseMe()
    container.register_local_value(int, 2, on_registry_close=cm.close)

    assert container._lazy_local_registry._on_close
    assert 2 == container.get(int)

    container.close()

    assert not container._lazy_local_registry._on_close
    assert cm.is_closed


def test_local_registry_is_lazy_but_only_once(container):
    """
    The local registry is created on first use and then kept using.
    """
    assert container._lazy_local_registry is None

    container.register_local_value(int, 1)

    reg = container._lazy_local_registry

    container.register_local_value(int, 2)

    assert reg is container._lazy_local_registry


@pytest.mark.asyncio
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
        registry.register_value(AnotherService, 23)

        assert [42, 23] == (await container.aget(Service, AnotherService))
        assert [42, 23] == (await container.aget(Service, AnotherService))

    async def test_aget_abstract_works_with_value(self, registry, container):
        """
        A value instead of a factory does not break aget_abstract().
        """
        registry.register_value(int, 42)
        registry.register_value(str, "42")

        assert [42, "42"] == (await container.aget_abstract(int, str))
        assert [42, "42"] == (await container.aget_abstract(int, str))

    async def test_aget_enter_false(self, registry, container):
        """
        If the factory is registered with enter=False and returns a context
        manager, it is not entered on instantiation.
        """
        entered = False

        @asynccontextmanager
        async def factory():
            nonlocal entered
            entered = True
            yield 42

        registry.register_factory(Service, factory, enter=False)

        cm = await container.aget(Service)

        assert not entered
        assert isinstance(cm, AbstractAsyncContextManager)

        async with cm as i:
            assert 42 == i

        assert entered

    async def test_passes_container_bc_name(self, registry, container):
        """
        If the factory takes an argument called `svcs_container`, it is passed on
        instantiation.
        """

        async def factory(svcs_container):
            return str(svcs_container.get(int))

        registry.register_value(int, 42)
        registry.register_factory(str, factory)

        assert "42" == await container.aget(str)

    async def test_passes_container_bc_annotation(self, registry, container):
        """
        If the factory takes an argument annotated with svcs.Container, it is
        passed on instantiation.
        """

        async def factory(foo: svcs.Container):
            return str(foo.get(int))

        registry.register_value(int, 42)
        registry.register_factory(str, factory)

        assert "42" == await container.aget(str)

    async def test_async_cleanup(self, registry, container, close_me):
        """
        Async cleanups are handled by aclose.
        """

        async def factory():
            await asyncio.sleep(0)

            yield Service()

            await asyncio.sleep(0)
            await close_me.aclose()

        registry.register_factory(Service, factory)

        svc = await container.aget(Service)

        assert 1 == len(container._on_close)
        assert Service() == svc
        assert not close_me.is_aclosed

        await container.aclose()

        assert close_me.is_aclosed
        assert not container._instantiated
        assert not container._on_close

    @pytest.mark.asyncio
    async def test_aclose_resilient(
        self, container, registry, caplog, close_me
    ):
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

        async def factory_no_boom():
            yield 3

            await close_me.aclose()

        registry.register_factory(Service, factory)
        registry.register_factory(AnotherService, async_factory)
        registry.register_factory(YetAnotherService, factory_no_boom)

        assert 1 == container.get(Service)
        assert 2 == await container.aget(AnotherService)
        assert 3 == await container.aget(YetAnotherService)

        assert not close_me.is_aclosed

        await container.aclose()

        # Inverse order
        assert (
            "tests.ifaces.AnotherService"
            == caplog.records[0].svcs_service_name
        )
        assert "tests.ifaces.Service" == caplog.records[1].svcs_service_name
        assert close_me.is_aclosed
        assert not container._instantiated
        assert not container._on_close

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

    async def test_none_is_a_valid_factory_result(self, registry, container):
        """
        None is a valid factory result and is cached as such.
        """

        i = 0

        async def factory():
            nonlocal i
            i += 1
            yield None

        registry.register_factory(Service, factory)

        assert None is await container.aget(Service)
        assert None is await container.aget(Service)
        assert 1 == i

        await container.aclose()

    async def test_local_factory_overrides_global_factory(
        self, registry, container
    ):
        """
        A container-local factory takes precedence over a global one. An
        aclosed container also acloses the registry.
        """
        cm = CloseMe()
        container.register_local_factory(
            int, async_int_factory, on_registry_close=cm.aclose
        )
        registry.register_value(int, 23)

        async with container:
            assert 42 == await container.aget(int)

        assert cm.is_aclosed
