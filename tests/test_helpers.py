# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Tests for svcs.helpers.autowire.
"""

from dataclasses import InitVar, dataclass
from typing import Annotated, NewType

import pytest

from svcs.exceptions import ServiceNotFoundError
from svcs.helpers import aautowire, autowire
from tests.ifaces import AnotherService, Interface, Service, YetAnotherService


# Autouse fixture to register service instances
@pytest.fixture(autouse=True)
def register_services(registry):
    registry.register_value(Service, Service())
    registry.register_value(AnotherService, AnotherService())
    registry.register_value(YetAnotherService, YetAnotherService())


class TestAutowireFunction:
    def test_autowire_multiple_dependencies(self, registry, container):
        """
        autowire resolves multiple different service types.
        """

        @autowire
        def func(svc: Service, another: AnotherService) -> list:
            return [svc, another]

        registry.register_factory(list, func)

        result = container.get(list)

        assert container.get(Service, AnotherService) == result

    def test_autowire_keyword_arg_with_default(self, registry, container):
        """
        autowire uses the default value if a keyword parameter
        cannot be found in the container.
        """

        @autowire
        def func(svc: Service, optional: str | None = None):
            return [svc, optional]

        registry.register_factory(list, func)

        result = container.get(list)

        assert [container.get(Service), None] == result

    def test_autowire_keyword_arg_required(self, registry, container):
        """
        autowire raises ServiceNotFoundError if a required keyword
        parameter cannot be found in the container.
        """

        @autowire
        def func(svc: Service, required: str): ...

        registry.register_factory(tuple, func)

        with pytest.raises(ServiceNotFoundError):
            container.get(tuple)

    def test_autowire_positional_only(self, registry, container):
        """
        autowire resolves multiple positional-only parameters.
        """

        @autowire
        def func(
            svc: Service,
            another: AnotherService,
            /,
            yet_another: YetAnotherService,
        ):
            return [svc, another, yet_another]

        registry.register_factory(list, func)

        result = container.get(list)

        assert (
            container.get(Service, AnotherService, YetAnotherService) == result
        )

    def test_autowire_keyword_only(self, registry, container):
        """
        autowire resolves keyword-only parameters from the container.
        """

        @autowire
        def func(*, svc: Service, another: AnotherService):
            return [svc, another]

        registry.register_factory(list, func)

        result = container.get(list)

        assert container.get(Service, AnotherService) == result

    @pytest.mark.parametrize(
        "special_type",
        [
            pytest.param(NewType("SuperService", Service), id="NewType"),
            pytest.param(Annotated[Service, "primary"], id="Annotated"),
            pytest.param(Interface, id="Protocol"),
        ],
    )
    def test_autowire_special_types(self, registry, container, special_type):
        """
        autowire resolves special-typed parameters correctly.
        """

        @autowire
        def func(user_id: special_type) -> object:
            return user_id

        registry.register_value(special_type, expected := object())
        registry.register_factory(object, func)

        result = container.get(object)

        assert expected == result

    def test_autowire_ignores_variadic_args(self, registry, container):
        """
        autowire ignores *args and **kwargs during injection.
        """

        @autowire
        def func(svc: Service, *args: str, **kwargs: int) -> tuple:
            return (svc, args, kwargs)

        registry.register_factory(tuple, func)

        result = container.get(tuple)

        assert result == (container.get(Service), (), {})


class TestAutowireClass:
    def test_autowire_class_single(self, registry, container):
        """
        autowire resolves dependencies for a single required argument.
        """

        @dataclass
        class MyClass:
            svc: Service

        registry.register_factory(MyClass, autowire(MyClass))

        assert MyClass(container.get(Service)) == container.get(MyClass)

    def test_autowire_class_multiple(self, registry, container):
        """
        autowire resolves multiple different service types for class.
        """

        @dataclass
        class MyClass:
            svc: Service
            another: AnotherService

        registry.register_factory(MyClass, autowire(MyClass))

        assert MyClass(
            container.get(Service), container.get(AnotherService)
        ) == container.get(MyClass)

    def test_autowire_class_optional(self, registry, container):
        """
        autowire uses default value for missing keyword argument in class.
        """

        @dataclass
        class MyClass:
            svc: Service
            optional: str = None

        registry.register_factory(MyClass, autowire(MyClass))

        assert MyClass(container.get(Service), None) == container.get(MyClass)

    def test_autowire_class_keyword_only(self, registry, container):
        """
        autowire resolves keyword-only parameters for class.
        """

        @dataclass(init=False)
        class MyClass:
            svc: Service
            another: AnotherService

            def __init__(self, *, svc: Service, another: AnotherService):
                self.svc = svc
                self.another = another

        registry.register_factory(MyClass, autowire(MyClass))

        assert MyClass(
            svc=container.get(Service), another=container.get(AnotherService)
        ) == container.get(MyClass)

    def test_autowire_class_positional_only(self, registry, container):
        """
        autowire resolves positional-only parameters for class.
        """

        @dataclass(init=False)
        class MyClass:
            def __init__(
                self,
                svc: Service,
                another: AnotherService,
                /,
                yet_another: YetAnotherService,
            ):
                self.svc = svc
                self.another = another
                self.yet_another = yet_another

        registry.register_factory(MyClass, autowire(MyClass))

        assert MyClass(
            container.get(Service),
            container.get(AnotherService),
            container.get(YetAnotherService),
        ) == container.get(MyClass)

    @pytest.mark.parametrize(
        ("special_type", "field_name"),
        [
            (NewType("SuperService", Service), "super_service"),
            (Annotated[Service, "primary"], "annotated_service"),
            (Interface, "protocol"),
        ],
    )
    def test_autowire_class_special_types(
        self, registry, container, special_type, field_name
    ):
        """
        autowire resolves special-typed parameters for class.
        """

        class MyClass:
            def __init__(self, value: special_type):
                self.value = value

        expected = object()
        registry.register_value(special_type, expected)
        registry.register_factory(MyClass, autowire(MyClass))

        assert container.get(MyClass).value == expected

    def test_autowire_class_initvar(self, registry, container):
        """
        autowire unwraps InitVar[T] annotations correctly.
        """

        @dataclass
        class MyClass:
            service: Service
            config: InitVar[str]

            def __post_init__(self, config: InitVar[str]):
                self.config = config

        registry.register_value(str, "configured")
        registry.register_factory(MyClass, autowire(MyClass))

        instance = container.get(MyClass)

        assert instance.service == container.get(Service)
        assert instance.config == "configured"


@pytest.mark.asyncio
class TestAAutowireFunction:
    async def test_aautowire_multiple_dependencies(self, registry, container):
        """
        aautowire resolves multiple different service types.
        """

        @aautowire
        async def func(svc: Service, another: AnotherService) -> list:
            return [svc, another]

        registry.register_factory(list, func)

        result = await container.aget(list)

        assert await container.aget(Service, AnotherService) == result

    async def test_aautowire_keyword_arg_with_default(
        self, registry, container
    ):
        """
        aautowire uses the default value if a keyword parameter
        cannot be found in the container.
        """

        @aautowire
        async def func(svc: Service, optional: str | None = None) -> list:
            return [svc, optional]

        registry.register_factory(list, func)

        result = await container.aget(list)

        assert [await container.aget(Service), None] == result

    async def test_aautowire_keyword_arg_required(self, registry, container):
        """
        aautowire raises ServiceNotFoundError if a required keyword
        parameter cannot be found in the container.
        """

        @aautowire
        async def func(svc: Service, required: str): ...

        registry.register_factory(tuple, func)

        with pytest.raises(ServiceNotFoundError):
            await container.aget(tuple)

    async def test_aautowire_positional_only(self, registry, container):
        """
        aautowire resolves multiple positional-only parameters.
        """

        @aautowire
        async def func(
            svc: Service,
            another: AnotherService,
            /,
            yet_another: YetAnotherService,
        ):
            return [svc, another, yet_another]

        registry.register_factory(list, func)

        result = await container.aget(list)

        assert (
            await container.aget(Service, AnotherService, YetAnotherService)
            == result
        )

    async def test_aautowire_keyword_only(self, registry, container):
        """
        aautowire resolves keyword-only parameters from the container.
        """

        @aautowire
        async def func(*, svc: Service, another: AnotherService):
            return [svc, another]

        registry.register_factory(list, func)

        result = await container.aget(list)

        assert await container.aget(Service, AnotherService) == result

    @pytest.mark.parametrize(
        "special_type",
        [
            pytest.param(NewType("SuperService", Service), id="NewType"),
            pytest.param(Annotated[Service, "primary"], id="Annotated"),
            pytest.param(Interface, id="Protocol"),
        ],
    )
    async def test_aautowire_special_types(
        self, registry, container, special_type
    ):
        """
        aautowire resolves special-typed parameters correctly.
        """

        @aautowire
        async def func(user_id: special_type) -> object:
            return user_id

        registry.register_value(special_type, expected := object())
        registry.register_factory(object, func)

        result = await container.aget(object)

        assert expected == result

    async def test_aautowire_ignores_variadic_args(self, registry, container):
        """
        aautowire ignores *args and **kwargs during injection.
        """

        @aautowire
        async def func(svc: Service, *args: str, **kwargs: int) -> tuple:
            return (svc, args, kwargs)

        registry.register_factory(tuple, func)

        result = await container.aget(tuple)

        assert result == (await container.aget(Service), (), {})


@pytest.mark.asyncio
class TestAAutowireClass:
    async def test_aautowire_class_single(self, registry, container):
        """
        aautowire resolves dependencies for a single required argument.
        """

        @dataclass
        class MyClass:
            svc: Service

        registry.register_factory(MyClass, aautowire(MyClass))

        assert MyClass(await container.aget(Service)) == await container.aget(
            MyClass
        )

    async def test_aautowire_class_multiple(self, registry, container):
        """
        aautowire resolves multiple different service types for class.
        """

        @dataclass
        class MyClass:
            svc: Service
            another: AnotherService

        registry.register_factory(MyClass, aautowire(MyClass))

        assert MyClass(
            await container.aget(Service), await container.aget(AnotherService)
        ) == await container.aget(MyClass)

    async def test_aautowire_class_optional(self, registry, container):
        """
        aautowire uses default value for missing keyword argument in class.
        """

        @dataclass
        class MyClass:
            svc: Service
            optional: str = None

        registry.register_factory(MyClass, aautowire(MyClass))

        assert MyClass(
            await container.aget(Service), None
        ) == await container.aget(MyClass)

    async def test_aautowire_class_keyword_only(self, registry, container):
        """
        aautowire resolves keyword-only parameters for class.
        """

        @dataclass(init=False)
        class MyClass:
            svc: Service
            another: AnotherService

            def __init__(self, *, svc: Service, another: AnotherService):
                self.svc = svc
                self.another = another

        registry.register_factory(MyClass, aautowire(MyClass))

        assert MyClass(
            svc=await container.aget(Service),
            another=await container.aget(AnotherService),
        ) == await container.aget(MyClass)

    async def test_aautowire_class_positional_only(self, registry, container):
        """
        aautowire resolves positional-only parameters for class.
        """

        @dataclass(init=False)
        class MyClass:
            def __init__(
                self,
                svc: Service,
                another: AnotherService,
                /,
                yet_another: YetAnotherService,
            ):
                self.svc = svc
                self.another = another
                self.yet_another = yet_another

        registry.register_factory(MyClass, aautowire(MyClass))

        assert MyClass(
            await container.aget(Service),
            await container.aget(AnotherService),
            await container.aget(YetAnotherService),
        ) == await container.aget(MyClass)

    @pytest.mark.parametrize(
        ("special_type", "field_name"),
        [
            (NewType("SuperService", Service), "super_service"),
            (Annotated[Service, "primary"], "annotated_service"),
            (Interface, "protocol"),
        ],
    )
    async def test_aautowire_class_special_types(
        self, registry, container, special_type, field_name
    ):
        """
        aautowire resolves special-typed parameters for class.
        """

        class MyClass:
            def __init__(self, value: special_type):
                self.value = value

        expected = object()
        registry.register_value(special_type, expected)
        registry.register_factory(MyClass, aautowire(MyClass))

        assert (await container.aget(MyClass)).value == expected

    async def test_aautowire_class_initvar(self, registry, container):
        """
        aautowire unwraps InitVar[T] annotations correctly.
        """

        @dataclass
        class MyClass:
            service: Service
            config: InitVar[str]

            def __post_init__(self, config: InitVar[str]):
                self.config = config

        registry.register_value(str, "configured")
        registry.register_factory(MyClass, aautowire(MyClass))

        instance = await container.aget(MyClass)

        assert instance.service == await container.aget(Service)
        assert instance.config == "configured"
