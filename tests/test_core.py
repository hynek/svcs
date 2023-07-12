from unittest.mock import Mock

import pytest

import svc_reg


class Service:
    pass


class AnotherService:
    pass


@pytest.fixture(name="rs")
def _rs(svc):
    return svc_reg.RegisteredService(Service, Service, None, None)


@pytest.fixture(name="container")
def _container(registry):
    return svc_reg.Container(registry)


@pytest.fixture(name="svc")
def _svc():
    return Service()


@pytest.fixture(name="registry")
def _registry():
    return svc_reg.Registry()


def nop_cleanup(svc):
    pass


# class TestRegistry:


class TestContainer:
    def test_register_factory_get(self, registry, container):
        """
        register_factory registers a factory and get returns the service.

        The service is cached.
        """
        registry.register_factory(Service, Service)

        svc = container.get(Service)

        assert isinstance(svc, Service)
        assert svc is container.get(Service)

    def test_register_value_get(self, registry, container, svc):
        """
        register_value registers a service object and get returns it.
        """
        registry.register_value(Service, svc)

        assert svc is container.get(Service)
        assert svc is container.get(Service)

    def test_get_not_found(self, container):
        """
        Asking for a service that isn't registered raises a ServiceNotFoundError.
        """
        with pytest.raises(svc_reg.ServiceNotFoundError) as ei:
            container.get(Service)

        assert Service is ei.value.args[0]

    def test_get_pings_empty(self, container):
        """
        get_pings returns an empty list if there are no pings.
        """
        assert [] == container.get_pings()

    def test_get_pings(self, registry, container, svc):
        """
        get_pings returns a list of ServicePings.
        """
        registry.register_factory(AnotherService, AnotherService)
        registry.register_value(Service, svc, ping=lambda _: None)

        assert [Service] == [
            ping._rs.svc_type for ping in container.get_pings()
        ]

    def test_add_get_instance_cleanup(self, container, svc):
        """
        _add_instance adds the service with its cleanup to the container and
        get_instance retrieves it.
        """
        rs = svc_reg.RegisteredService(Service, Service, nop_cleanup, None)

        container._add_instance(rs, svc)

        assert svc is container._get_instance(rs.svc_type)
        assert [(rs, svc)] == container.cleanups

    def test_add_get_instance_no_cleanup(self, container, svc, rs):
        """
        _add_instance adds the service with its cleanup to the container and
        get_instance retrieves it.
        """
        container._add_instance(rs, svc)

        assert svc is container._get_instance(rs.svc_type)
        assert [] == container.cleanups

    def test_add_cleanup_added(self, container, svc):
        """
        If the registered service has a cleanup, it is added to the cleanup
        and add_cleanup returns True.
        """

        rs = svc_reg.RegisteredService(Service, Service, nop_cleanup, None)

        assert container.add_cleanup(rs, svc)
        assert [(rs, svc)] == container.cleanups

    def test_add_cleanup_not_added(self, container, rs, svc):
        """
        If the registered service has no cleanup, it's not added and
        add_cleanup returns False.
        """
        assert False is container.add_cleanup(rs, svc)
        assert [] == container.cleanups

    def test_forget_service_type_nothing_registered(self, container):
        """
        forget_service_type does nothing if nothing has been registered.
        """
        container.forget_service_type(Service)

    def test_forget_service_type_no_cleanup(self, container, rs, svc):
        """
        forget_service_type removes the registered service from the container.
        """
        container._add_instance(rs, svc)

        container.forget_service_type(Service)

        assert {} == container.instantiated
        assert [] == container.cleanups

    def test_forget_service_type_with_cleanup(self, container, svc):
        """
        forget_service_type removes the registered service from the container.
        """
        rs = svc_reg.RegisteredService(
            Service, svc, Mock(spec_set=["__call__"]), None
        )
        container._add_instance(rs, svc)

        container.forget_service_type(Service)

        assert {} == container.instantiated

    def test_forget_service_type_is_ok_with_other_registrations(
        self, container, registry
    ):
        """
        If other svc_reg are registered, they are ignored by the cleanup
        purge.
        """
        registry.register_factory(Service, Service, cleanup=lambda _: None)
        registry.register_factory(
            AnotherService, AnotherService, cleanup=lambda _: None
        )

        container.get(Service)
        container.get(AnotherService)

        assert 2 == len(container.cleanups)

        container.forget_service_type(Service)
        registry.register_value(Service, object(), cleanup=nop_cleanup)

        container.get(Service)
        container.get(AnotherService)

        assert 3 == len(container.cleanups)

    def test_repr(self, container, rs, svc):
        """
        The repr counts correctly.
        """
        rs2 = svc_reg.RegisteredService(
            AnotherService, svc, Mock(spec_set=["__call__"]), None
        )

        container._add_instance(rs, Service())
        container._add_instance(rs2, Service())

        assert (
            "<Container(instantiated=2, cleanups=1, async_cleanups=0>"
            == repr(container)
        )

    def test_cleanup_called(self, container, rs):
        """
        Services that have a cleanup have them called on cleanup.
        """
        container._add_instance(rs, Service())

        svc = AnotherService()
        rs_cleanup = svc_reg.RegisteredService(
            AnotherService, AnotherService, Mock(spec_set=["__call__"]), None
        )
        container._add_instance(rs_cleanup, svc)

        container.cleanup()

        rs_cleanup.cleanup.assert_called_once_with(svc)


class TestRegisteredService:
    def test_repr(self, rs):
        """
        repr uses the fully-qualified name of a svc type.
        """

        assert (
            "<RegisteredService(svc_type=tests.test_core.Service, has_cleanup=False, has_ping=False)>"
        ) == repr(rs)

    def test_name(self, rs):
        """
        The name property deducts the correct class name.
        """

        assert "Service" == rs.name


class TestServicePing:
    def test_name(self, rs):
        """
        The name property proxies the correct class name.
        """

        assert "Service" == svc_reg.ServicePing(None, rs).name

    def test_ping(self):
        """
        Calling ping instantiates the service using its factory, appends it to
        the cleanup list, and calls the service's ping method.
        """

        svc = Service()
        rs = svc_reg.RegisteredService(
            Service,
            lambda: svc,
            Mock(spec_set=["__call__"]),
            Mock(spec_set=["__call__"]),
        )
        container = svc_reg.Container(svc_reg.Registry())
        svc_ping = svc_reg.ServicePing(container, rs)

        svc_ping.ping()

        rs.ping.assert_called_once_with(svc)
        assert [(rs, svc)] == container.cleanups
