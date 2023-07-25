# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

import pytest

import svcs


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


class Interface:
    pass


class Service1:
    pass


class Service2:
    pass


@pytest.mark.usefixtures("clean_app_ctx")
class TestFlask:
    def test_cleanup_added(self, registry):
        """
        get() handles the case where there is already a cleanup registered.
        """

        cleanup1 = Mock()
        cleanup2 = Mock()

        def factory1():
            yield Service1()
            cleanup1()

        def factory2():
            yield Service2()
            cleanup2()

        registry.register_factory(Service1, factory1)
        svcs.flask.replace_factory(Service2, factory2)

        svc1 = svcs.flask.get(Service1)
        svc2 = svcs.flask.get(Service2)

        assert isinstance(svc1, Service1)
        assert isinstance(svc2, Service2)
        assert 2 == len(flask.g.svc_container.cleanups)

        teardown(None)

        cleanup1.assert_called_once_with()
        cleanup2.assert_called_once_with()

    def test_overwrite_value(self, registry):
        """
        It's possible to overwrite an already registered type.
        """
        registry.register_value(Interface, Interface(), ping=lambda _: None)

        assert isinstance(svcs.flask.get(Interface), Interface)

        svcs.flask.replace_value(Interface, Service2())

        assert isinstance(svcs.flask.get(Interface), Service2)
        assert [] == svcs.flask.get_pings()

    def test_overwrite_factory(self, container):
        """
        It's possible to overwrite an already registered type using a factory.
        """
        svcs.flask.replace_value(Interface, Interface(), ping=lambda _: None)

        assert isinstance(svcs.flask.get(Interface), Interface)

        svcs.flask.replace_factory(Interface, Service2)

        assert isinstance(svcs.flask.get(Interface), Service2)
        assert [] == svcs.flask.get_pings()

    def test_cache(self):
        """
        Getting a service twice within the same request returns the same
        object.
        """
        svcs.flask.replace_factory(Interface, Service1)

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
        svcs.flask.replace_factory(Service1, Service1)
        svcs.flask.replace_factory(Service2, Service2, ping=lambda _: None)

        assert [Service2] == [
            ping._rs.svc_type for ping in svcs.flask.get_pings()
        ]

    def test_cleanup_purge_tolerant(self, container):
        """
        If other svcs are registered, they are ignored by the cleanup
        purge.
        """

        def factory1():
            yield Service1()

        def factory2():
            yield Service2()

        svcs.flask.replace_factory(Service1, factory1)
        svcs.flask.replace_factory(Service2, factory2)

        svcs.flask.get(Service1)
        svcs.flask.get(Service2)

        assert 2 == len(container.cleanups)

        svcs.flask.replace_factory(Service1, Interface)

        svcs.flask.get(Service1)
        svcs.flask.get(Service2)

        assert 2 == len(container.cleanups)

    @pytest.mark.asyncio()
    async def test_teardown_warns_on_async_cleanups(self, container):
        """
        teardown() warns if there are async cleanups.
        """

        async def factory():
            yield Service1()

        svcs.flask.replace_factory(Service1, factory)

        await container.aget(Service1)

        with pytest.warns(UserWarning) as wi:
            teardown(None)

        w = wi.pop()

        assert 0 == len(wi.list)
        assert (
            "Skipped async cleanup for "
            "<RegisteredService(svc_type=tests.test_flask.Service1, "
            "has_ping=False)>. Use aclose() instead." == w.message.args[0]
        )


class TestNonContextHelpers:
    def test_register_factory_helper(self, registry, app):
        """
        register_factory() registers a factory to the app that is passed.
        """
        svcs.flask.init_app(app, registry)

        svcs.flask.register_factory(app, Interface, Service1)

        assert Interface in registry.services

    def test_register_value_helper(self, registry, app):
        """
        register_value() registers a value to the app that is passed.
        """
        svcs.flask.init_app(app, registry)

        svcs.flask.register_value(app, Interface, 42)

        assert Interface in registry.services


class TestInitApp:
    def test_implicit_registry(self):
        """
        init_app() creates a registry if one isn't provided.
        """
        app = flask.Flask("tests")
        svcs.flask.init_app(app)

        assert isinstance(app.config["svcsistry"], svcs.Registry)

    def test_explicit_registry(self):
        """
        If a registry is passsed to init_app(), it's used.
        """
        registry = svcs.Registry()
        app = flask.Flask("tests")
        svcs.flask.init_app(app, registry)

        assert registry is app.config["svcsistry"]
