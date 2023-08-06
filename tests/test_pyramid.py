from unittest.mock import Mock

import pytest

import svcs

from .fake_factories import int_factory
from .ifaces import AnotherService, Service


try:
    import webtest

    from pyramid.config import Configurator
    from pyramid.view import view_config
except ImportError:
    pytest.skip("Pyramid not installed", allow_module_level=True)


def make_config(view=None):
    config = Configurator(settings={})
    svcs.pyramid.init(config)

    if view is not None:
        config.add_route(view, "/")
    config.scan()

    return config


def make_test_app(view=None):
    config = make_config(view)

    return webtest.TestApp(config.make_wsgi_app())


@pytest.fixture(name="config")
def _config():
    return make_config()


def test_close_nop():
    """
    Closing a config that has no svcs_registry does nothing.
    """
    svcs.pyramid.close_registry(Mock(registry={}))


def test_close(config):
    """
    Closing a config with svcs_registry calls on_registry_close hooks on the
    registered svcs.pyramid.
    """
    orc = Mock()

    svcs.pyramid.register_factory(
        config, int, int_factory, on_registry_close=orc
    )

    svcs.pyramid.close_registry(config)

    assert orc.called


@view_config(route_name="tl_view", renderer="json")
def tl_view(request):
    """
    Thread locals return the same objects as the direct way.
    """
    svc = svcs.pyramid.get(Service)

    assert (
        svc == request.svcs.get(Service) == svcs.pyramid.get_abstract(Service)
    )
    assert (
        request.registry["svcs_registry"]
        is svcs.pyramid.get_registry()
        is svcs.pyramid.get_registry(request)
    )
    assert (
        request.svcs
        is svcs.pyramid.get_container()
        is svcs.pyramid.get_container(request)
    )

    return {"svc": svc}


def test_thread_locals():
    """
    Thread locals are available in views.
    """
    tapp = make_test_app("tl_view")

    svcs.pyramid.get_registry(tapp.app).register_value(Service, 42)
    svcs.pyramid.register_value(tapp.app, AnotherService, 23)

    assert {"svc": 42} == tapp.get("/").json
