# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

import pytest

import svcs

from .fake_factories import nop
from .ifaces import AnotherService, Interface, Service


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
    svcs.flask.init_app(app, registry)
    with app.app_context() as ctx:
        yield ctx


@pytest.fixture(name="container")
def _container(clean_app_ctx):
    return svcs.flask._ensure_req_data()[1]


@pytest.mark.usefixtures("clean_app_ctx")
class TestFlask:
    def test_cleanup_added(self, registry):
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
        svcs.flask.replace_factory(AnotherService, factory2)

        svc1 = svcs.flask.get(Service)
        svc2 = svcs.flask.get(AnotherService)

        assert isinstance(svc1, Service)
        assert isinstance(svc2, AnotherService)
        assert 2 == len(flask.g.svcs_container._on_close)

        teardown(None)

        cleanup1.assert_called_once_with()
        cleanup2.assert_called_once_with()

    def test_overwrite_value(self, registry):
        """
        It's possible to overwrite an already registered type.
        """
        registry.register_value(Interface, Service(), ping=nop)

        assert isinstance(svcs.flask.get(Interface), Interface)

        svcs.flask.replace_value(Interface, AnotherService())

        assert isinstance(svcs.flask.get(Interface), AnotherService)
        assert [] == svcs.flask.get_pings()

    def test_overwrite_factory(self):
        """
        It's possible to overwrite an already registered type using a factory.
        """
        svcs.flask.replace_value(Interface, Service(), ping=nop)

        assert isinstance(svcs.flask.get(Interface), Interface)

        svcs.flask.replace_factory(Interface, AnotherService)

        assert isinstance(svcs.flask.get(Interface), AnotherService)
        assert [] == svcs.flask.get_pings()

    def test_cache(self):
        """
        Getting a service twice within the same request returns the same
        object.
        """
        svcs.flask.replace_factory(Interface, Service)

        assert svcs.flask.get(Interface) is svcs.flask.get(Interface)

    def test_not_found(self):
        """
        Trying to get a service that hasn't been registered raises a
        ServiceNotFoundError.
        """
        with pytest.raises(svcs.exceptions.ServiceNotFoundError):
            svcs.flask.get(Interface)

    def test_get_pingeable(self):
        """
        get_pingable returns only pingable svcs.
        """
        svcs.flask.replace_factory(Service, Service)
        svcs.flask.replace_factory(AnotherService, AnotherService, ping=nop)

        assert [AnotherService] == [
            ping._rs.svc_type for ping in svcs.flask.get_pings()
        ]

    def test_cleanup_purge_tolerant(self, container):
        """
        If other svcs are registered, they are ignored by the cleanup
        purge.
        """

        def factory1():
            yield Service()

        def factory2():
            yield AnotherService()

        svcs.flask.replace_factory(Interface, factory1)
        svcs.flask.replace_factory(AnotherService, factory2)

        svcs.flask.get(Interface)
        svcs.flask.get(AnotherService)

        assert 2 == len(container._on_close)

        svcs.flask.replace_factory(Interface, Service)

        svcs.flask.get(Interface)
        svcs.flask.get(AnotherService)

        assert 2 == len(container._on_close)

    @pytest.mark.asyncio()
    async def test_teardown_warns_on_async_on_close(self, container):
        """
        teardown() warns if there are async cleanups.
        """

        async def factory():
            yield Service()

        svcs.flask.replace_factory(Service, factory)

        await container.aget(Service)

        with pytest.warns(UserWarning) as wi:
            teardown(None)

        w = wi.pop()

        assert 0 == len(wi.list)
        assert (
            "Skipped async cleanup for 'tests.ifaces.Service'. "
            "Use aclose() instead." == w.message.args[0]
        )


class TestNonContextHelpers:
    def test_register_factory_helper(self, registry, app):
        """
        register_factory() registers a factory to the app that is passed.
        """
        svcs.flask.init_app(app, registry)

        svcs.flask.register_factory(app, Interface, Service)

        assert Interface in registry._services

    def test_register_value_helper(self, registry, app):
        """
        register_value() registers a value to the app that is passed.
        """
        svcs.flask.init_app(app, registry)

        svcs.flask.register_value(app, Interface, 42)

        assert Interface in registry._services


class TestInitApp:
    def test_implicit_registry(self):
        """
        init_app() creates a registry if one isn't provided.
        """
        app = flask.Flask("tests")
        svcs.flask.init_app(app)

        assert isinstance(app.config["svcs_registry"], svcs.Registry)

    def test_explicit_registry(self):
        """
        If a registry is passed to init_app(), it's used.
        """
        registry = svcs.Registry()
        app = flask.Flask("tests")
        svcs.flask.init_app(app, registry)

        assert registry is app.config["svcs_registry"]


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
