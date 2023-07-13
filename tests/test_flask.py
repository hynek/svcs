from unittest.mock import Mock

import pytest

import svc_reg


try:
    import flask

    from svc_reg.flask import teardown
except ImportError:
    pytest.skip("Flask not installed", allow_module_level=True)


@pytest.fixture(name="app")
def _app():
    return flask.Flask("tests")


@pytest.fixture(name="clean_app_ctx")
def _clean_app_ctx(registry, app):
    svc_reg.flask.init_app(app, registry)
    with app.app_context() as ctx:
        yield ctx


@pytest.fixture(name="registry")
def _registry():
    return svc_reg.Registry()


@pytest.fixture(name="container")
def _container(clean_app_ctx):
    return svc_reg.flask._ensure_req_data()[1]


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

        cleanup1 = Mock(return_value=None)
        cleanup2 = Mock(return_value=None)

        registry.register_factory(Service1, Service1, cleanup=cleanup1)
        svc_reg.flask.replace_factory(Service2, Service2, cleanup=cleanup2)

        svc1 = svc_reg.flask.get(Service1)
        svc2 = svc_reg.flask.get(Service2)

        assert isinstance(svc1, Service1)
        assert isinstance(svc2, Service2)

        teardown(None)

        cleanup1.assert_called_once_with(svc1)
        cleanup2.assert_called_once_with(svc2)

    def test_overwrite_value(self, registry, container):
        """
        It's possible to overwrite an already registered type. That type's
        cleanup is removed.
        """

        registry.register_value(
            Interface, Interface(), cleanup=lambda _: None, ping=lambda _: None
        )

        assert isinstance(svc_reg.flask.get(Interface), Interface)
        assert [] != container.cleanups

        svc_reg.flask.replace_value(Interface, Service2())

        assert isinstance(svc_reg.flask.get(Interface), Service2)
        assert [] == svc_reg.flask.get_pings()

    def test_overwrite_factory(self, container):
        """
        It's possible to overwrite an already registered type using a factory.
        """

        svc_reg.flask.replace_value(
            Interface, Interface(), cleanup=lambda _: None, ping=lambda _: None
        )

        assert isinstance(svc_reg.flask.get(Interface), Interface)
        assert [] != container.cleanups

        svc_reg.flask.replace_factory(Interface, Service2)

        assert isinstance(svc_reg.flask.get(Interface), Service2)
        assert [] == svc_reg.flask.get_pings()

    def test_cache(self):
        """
        Getting a service twice within the same request returns the same
        object.
        """
        svc_reg.flask.replace_factory(Interface, Service1)

        assert svc_reg.flask.get(Interface) is svc_reg.flask.get(Interface)

    def test_not_found(self):
        """
        Trying to get a service that hasn't been registered raises a
        ServiceNotFoundError.
        """
        with pytest.raises(svc_reg.ServiceNotFoundError):
            svc_reg.flask.get(Interface)

    def test_get_pingeable(self):
        """
        get_pingable returns only pingable svc_reg.
        """
        svc_reg.flask.replace_factory(Service1, Service1)
        svc_reg.flask.replace_factory(Service2, Service2, ping=lambda _: None)

        assert [Service2] == [
            ping._rs.svc_type for ping in svc_reg.flask.get_pings()
        ]

    def test_cleanup_purge_tolerant(self, container):
        """
        If other svc_reg are registered, they are ignored by the cleanup
        purge.
        """
        svc_reg.flask.replace_factory(
            Service1, Service1, cleanup=lambda _: None
        )
        svc_reg.flask.replace_factory(
            Service2, Service2, cleanup=lambda _: None
        )

        svc_reg.flask.get(Service1)
        svc_reg.flask.get(Service2)

        assert 2 == len(container.cleanups)
        assert 0 == len(container.async_cleanups)

        svc_reg.flask.replace_factory(Service1, Interface)

        svc_reg.flask.get(Service1)
        svc_reg.flask.get(Service2)

        assert 2 == len(container.cleanups)
        assert 0 == len(container.async_cleanups)

    def test_teardown_warns_on_async_cleanups(self, container):
        """
        teardown() warns if there are async cleanups.
        """

        async def cleanup(svc):
            pass

        rs = svc_reg.RegisteredService(
            Interface, lambda: Service1(), cleanup=cleanup, ping=None
        )

        container.add_cleanup(rs, rs.factory())

        with pytest.warns(UserWarning) as wi:
            teardown(None)

        w = wi.pop()

        assert 0 == len(wi.list)
        assert (
            "1 async cleanup(s) left, "
            "but svc-reg's Flask support does not support them automatically."
            == w.message.args[0]
        )


class TestNonContextHelpers:
    def test_register_factory_helper(self, registry, app):
        """
        register_factory() registers a factory to the app that is passed.
        """
        svc_reg.flask.init_app(app, registry)

        svc_reg.flask.register_factory(app, Interface, Service1)

        assert Interface in registry.services

    def test_register_value_helper(self, registry, app):
        """
        register_value() registers a value to the app that is passed.
        """
        svc_reg.flask.init_app(app, registry)

        svc_reg.flask.register_value(app, Interface, 42)

        assert Interface in registry.services


class TestInitApp:
    def test_implicit_registry(self):
        """
        init_app() creates a registry if one isn't provided.
        """
        app = flask.Flask("tests")
        svc_reg.flask.init_app(app)

        assert isinstance(app.config["svc_registry"], svc_reg.Registry)

    def test_explicit_registry(self):
        """
        If a registry is passsed to init_app(), it's used.
        """
        registry = svc_reg.Registry()
        app = flask.Flask("tests")
        svc_reg.flask.init_app(app, registry)

        assert registry is app.config["svc_registry"]
