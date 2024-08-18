# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

import pytest

import svcs

from tests.helpers import nop
from tests.ifaces import AnotherService, Interface, Service


try:
    import flask

    from svcs.flask import teardown
except ImportError:
    pytest.skip("Flask not installed", allow_module_level=True)


@pytest.fixture(name="app")
def _app():
    return flask.Flask("tests")


@pytest.fixture(name="clean_app_ctx")
def _clean_app_ctx(registry, app):
    svcs.flask.init_app(app, registry=registry)
    with app.app_context() as ctx:
        yield ctx


@pytest.fixture(name="container")
def _container(clean_app_ctx):
    return svcs.flask.svcs_from()


@pytest.mark.usefixtures("clean_app_ctx")
class TestFlask:
    def test_register_value_multiple(self, registry):
        """
        register_value registers a service object on an app and get returns as
        many values as are requeste.
        """
        registry.register_value(Service, 1)
        registry.register_value(AnotherService, 2)

        assert [1, 2] == svcs.flask.get(Service, AnotherService)
        assert [1, 2] == svcs.flask.get(Service, AnotherService)

    def test_cleanup_added(self, registry, app):
        """
        get() handles the case where there is already a cleanup registered.
        """

        cleanup1 = Mock()
        cleanup2 = Mock()

        def factory1():
            yield Service()
            cleanup1()

        def factory2():
            yield AnotherService()
            cleanup2()

        registry.register_factory(Service, factory1)
        svcs.flask.register_factory(app, AnotherService, factory2)

        svc1 = svcs.flask.get(Service)
        svc2 = svcs.flask.get(AnotherService)

        assert isinstance(svc1, Service)
        assert isinstance(svc2, AnotherService)
        assert 2 == len(flask.g.svcs_container._on_close)

        teardown(None)

        cleanup1.assert_called_once_with()
        cleanup2.assert_called_once_with()

    def test_overwrite_value(self, registry, app):
        """
        It's possible to overwrite an already registered and acquired type
        using a value. The container cache is cleared.
        """
        registry.register_value(Interface, Service(), ping=nop)

        assert isinstance(svcs.flask.get(Interface), Interface)

        container = svcs.flask.svcs_from()

        assert container._instantiated

        svcs.flask.overwrite_value(Interface, AnotherService())

        assert not container._instantiated

        assert isinstance(svcs.flask.get(Interface), AnotherService)
        assert [] == svcs.flask.get_pings()

    def test_overwrite_factory(self, app):
        """
        It's possible to overwrite an already registered and acquired type
        using a factory. The container cache is cleared.
        """
        svcs.flask.register_value(app, Interface, Service(), ping=nop)

        assert isinstance(svcs.flask.get(Interface), Interface)

        container = svcs.flask.svcs_from()

        assert container._instantiated

        svcs.flask.overwrite_factory(Interface, AnotherService)

        assert not container._instantiated

        assert isinstance(svcs.flask.get(Interface), AnotherService)
        assert [] == svcs.flask.get_pings()

    def test_cache(self, app):
        """
        Getting a service twice within the same request returns the same
        object.
        """
        svcs.flask.register_factory(app, Interface, Service)

        assert svcs.flask.get(Interface) is svcs.flask.get(Interface)

    def test_not_found(self):
        """
        Trying to get a service that hasn't been registered raises a
        ServiceNotFoundError.
        """
        with pytest.raises(svcs.exceptions.ServiceNotFoundError):
            svcs.flask.get(Interface)

    def test_get_pingeable(self, app):
        """
        get_pingable returns only pingable svcs.
        """
        svcs.flask.register_factory(app, Service, Service)
        svcs.flask.register_factory(
            app, AnotherService, AnotherService, ping=nop
        )

        assert [AnotherService] == [
            ping._svc_type for ping in svcs.flask.get_pings()
        ]

    @pytest.mark.asyncio
    async def test_teardown_warns_on_async_on_close(self, container):
        """
        teardown() warns if there are async cleanups.
        """

        async def factory():
            yield Service()

        container.registry.register_factory(Service, factory)

        await container.aget(Service)

        with pytest.warns(UserWarning) as wi:
            teardown(None)

        w = wi.pop()

        assert 0 == len(wi.list)
        assert (
            "Skipped async cleanup for 'tests.ifaces.Service'. "
            "Use aclose() instead." == w.message.args[0]
        )

    def test_register_factory_get_abstract(self, registry, container):
        """
        register_factory registers a factory and get_abstract returns the service.

        The service is cached.
        """
        registry.register_factory(Interface, Service)

        svc = container.get_abstract(Interface)

        assert isinstance(svc, Interface)
        assert svc is svcs.flask.get_abstract(Interface)

    def test_svcs_from(self, container):
        """
        svcs_from() returns the container the same container as that is on g.
        """
        assert (
            container
            is svcs.flask.svcs_from()
            is flask.g.svcs_container
            is svcs.flask.svcs_from()
        )

    def test_local_proxy_container(self, container):
        """
        svcs.flask.container is a LocalProxy that returns the same container as
        that is on g.
        """
        assert (
            container
            == flask.g.svcs_container
            == svcs.flask.svcs_from()
            == svcs.flask.container
        )

    def test_local_proxy_registry(self, registry, app):
        """
        svcs.flask.registry is a LocalProxy that returns the same container as
        that is on `flask.current_app`.
        """

        assert (
            registry
            == svcs.flask.get_registry(flask.current_app)
            == svcs.flask.get_registry(app)
            == svcs.flask.get_registry()
        )


class TestNonContextHelpers:
    def test_get_registry(self, registry, app):
        """
        get_registry() returns the registry that has been put on the app.
        """
        svcs.flask.init_app(app, registry=registry)

        assert registry is svcs.flask.get_registry(app)

    def test_register_factory_helper(self, registry, app):
        """
        register_factory() registers a factory to the app that is passed.
        """
        svcs.flask.init_app(app, registry=registry)

        svcs.flask.register_factory(app, Interface, Service)

        assert Interface in registry._services

    def test_register_value_helper(self, registry, app):
        """
        register_value() registers a value to the app that is passed.
        """
        svcs.flask.init_app(app, registry=registry)

        svcs.flask.register_value(app, Interface, 42)

        assert Interface in registry._services


class TestInitApp:
    def test_implicit_registry(self):
        """
        init_app() creates a registry if one isn't provided.
        """
        app = flask.Flask("tests")
        svcs.flask.init_app(app)

        assert isinstance(app.extensions["svcs_registry"], svcs.Registry)

    def test_explicit_registry(self):
        """
        If a registry is passed to init_app(), it's used.
        """
        registry = svcs.Registry()
        app = flask.Flask("tests")
        svcs.flask.init_app(app, registry=registry)

        assert registry is app.extensions["svcs_registry"]


class TestCloseRegistry:
    def test_nop(self):
        """
        close_registry() does nothing if there's no registry in app.
        """
        app = flask.Flask("tests")
        svcs.flask.close_registry(app)

    def test_closes(self, app):
        """
        close_registry() runs the registry's close() method.
        """
        close = Mock()

        svcs.flask.init_app(app)

        svcs.flask.register_factory(
            app, Interface, Service, on_registry_close=close
        )

        svcs.flask.close_registry(app)

        assert close.called
