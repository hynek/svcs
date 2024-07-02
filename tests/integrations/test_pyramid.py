# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

import pytest

import svcs

from tests.fake_factories import int_factory
from tests.helpers import nop
from tests.ifaces import AnotherService, Service


try:
    import httpx

    from pyramid.config import Configurator
    from pyramid.view import view_config
except ImportError:
    pytest.skip("Pyramid not installed", allow_module_level=True)


@pytest.fixture(name="config")
def _config():
    config = Configurator(settings={})
    svcs.pyramid.init(config)

    config.add_route("tl_view", "/tl")
    config.add_route("health_view", "/health")

    config.scan()

    return config


@pytest.fixture(name="app")
def _app(config):
    return config.make_wsgi_app()


@pytest.fixture(name="client")
def _client(app):
    return httpx.Client(
        transport=httpx.WSGITransport(app=app), base_url="http://example.com/"
    )


@pytest.fixture(name="rh", params=(0, 1))
def _rh(request, config, app):
    """
    A RegistryHaver fixture -- usually that's configs and apps.
    """
    return (config, app)[request.param]


def test_close_nop(rh):
    """
    Closing a config/app that has no svcs_registry does nothing.
    """
    svcs.pyramid.close_registry(Mock(registry={}))


def test_close(rh):
    """
    Closing a config/app with svcs_registry calls on_registry_close callbacks
    on the registered svcs.pyramid.
    """
    orc = Mock()

    svcs.pyramid.register_factory(rh, int, int_factory, on_registry_close=orc)

    svcs.pyramid.close_registry(rh)

    assert orc.called


@view_config(route_name="tl_view", renderer="json")
def tl_view(request):
    """
    Thread locals return the same objects as the direct way.
    """
    svc = svcs.pyramid.get(request, Service)
    svcs.pyramid.get(request, float)

    assert (
        svc
        is svcs.pyramid.get(request, Service)
        is svcs.pyramid.svcs_from(request).get(Service)
        is svcs.pyramid.get_abstract(request, Service)
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


@view_config(route_name="health_view", renderer="json")
def health_view(request):
    assert (
        svcs.pyramid.get_pings(request)
        == svcs.pyramid.svcs_from(request).get_pings()
    )
    return {"num": len(svcs.pyramid.svcs_from(request).get_pings())}


class TestIntergration:
    def test_get(self, app, client, close_me):
        """
        Service acquisition via svcs_get and thread locals works.
        """

        def closing_factory():
            yield 1.0

            close_me.close()

        svcs.pyramid.get_registry(app).register_value(Service, 42)
        svcs.pyramid.register_value(app, AnotherService, 23)
        svcs.pyramid.register_factory(app, float, closing_factory)

        assert {"svc": 42} == client.get("/tl").json()
        assert close_me.is_closed

    def test_get_pings(self, app, client):
        """
        get_pings() returns service pings with and without passing a request.
        """
        svcs.pyramid.get_registry(app).register_value(Service, 42, ping=nop)

        assert {"num": 1} == client.get("/health").json()
