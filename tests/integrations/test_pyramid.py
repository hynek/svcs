# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

import pytest

import svcs

from tests.fake_factories import int_factory, nop
from tests.ifaces import AnotherService, Service


try:
    import webtest

    from pyramid.config import Configurator
    from pyramid.view import view_config
except ImportError:
    pytest.skip("Pyramid not installed", allow_module_level=True)


def make_config():
    config = Configurator(settings={})
    svcs.pyramid.init(config)

    config.add_route("tl_view", "/tl")
    config.add_route("health_view", "/health")

    config.scan()

    return config


@pytest.fixture(name="tapp")
def _tapp(config):
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
    Closing a config with svcs_registry calls on_registry_close callbacks on
    the registered svcs.pyramid.
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
    svcs.pyramid.get(float)

    assert (
        svc
        is svcs.pyramid.svcs_from(request).get(Service)
        is svcs.pyramid.get_abstract(Service)
    )
    assert (
        request.registry["svcs_registry"]
        is svcs.pyramid.get_registry()
        is svcs.pyramid.get_registry(request)
    )
    assert (
        request.svcs_container
        is svcs.pyramid.svcs_from()
        is svcs.pyramid.svcs_from(request)
    )

    return {"svc": svc}


def test_thread_locals(tapp):
    """
    Thread locals are available in views.
    """
    closed = False

    def closing_factory():
        yield 1.0

        nonlocal closed
        closed = True

    svcs.pyramid.get_registry(tapp.app).register_value(Service, 42)
    svcs.pyramid.register_value(tapp.app, AnotherService, 23)
    svcs.pyramid.register_factory(tapp.app, float, closing_factory)

    assert {"svc": 42} == tapp.get("/tl").json
    assert closed


@view_config(route_name="health_view", renderer="json")
def health_view(request):
    assert (
        svcs.pyramid.get_pings(request)
        == svcs.pyramid.get_pings()
        == svcs.pyramid.svcs_from(request).get_pings()
    )
    return {"num": len(svcs.pyramid.svcs_from(request).get_pings())}


def test_get_pings(tapp):
    """
    get_pings() returns service pings with and without passing a request.
    """
    svcs.pyramid.get_registry(tapp.app).register_value(Service, 42, ping=nop)

    assert {"num": 1} == tapp.get("/health").json
