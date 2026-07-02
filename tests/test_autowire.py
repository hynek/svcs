# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Tests for svcs.autowire() and svcs.aautowire().
"""

from typing import Annotated, NewType

import pytest

from svcs import aautowire, autowire
from svcs.exceptions import ServiceNotFoundError
from tests.fake_factories import (
    async_list_ignores_variadic_args_factory,
    async_list_keyword_arg_with_default_factory,
    async_list_keyword_only_factory,
    async_list_multiple_dependencies_factory,
    async_list_positional_only_arg_with_default_factory,
    async_list_positional_only_factory,
    async_list_string_type_annotation_factory,
    list_ignores_variadic_args_factory,
    list_keyword_arg_with_default_factory,
    list_keyword_only_factory,
    list_multiple_dependencies_factory,
    list_positional_only_arg_with_default_factory,
    list_positional_only_factory,
    list_string_type_annotation_factory,
)
from tests.fake_services import (
    InitVarService,
    KeywordArgWithDefault,
    KeywordOnlyServices,
    MultipleServices,
    PositionalOnlyArgWithDefault,
    PositionalOnlyServices,
    SingleService,
    StringAnnotationService,
    VariadicArgs,
)
from tests.ifaces import (
    AnotherService,
    Interface,
    Service,
    YetAnotherService,
)


SPECIAL_TYPE_CASES = [
    pytest.param(NewType("SuperService", Service), id="NewType"),
    pytest.param(Annotated[Service, "primary"], id="Annotated"),
    pytest.param(Interface, id="Protocol"),
]
"""Special Python types that autowire should support when resolving dependencies."""


_service = Service()
_another_service = AnotherService()
_yet_another_service = YetAnotherService()


# Autouse fixture to register service instances
@pytest.fixture(autouse=True)
def register_services(registry):
    registry.register_value(Service, _service)
    registry.register_value(AnotherService, _another_service)
    registry.register_value(YetAnotherService, _yet_another_service)


class TestAutowireFunction:
    @pytest.mark.parametrize(
        ("func", "expected"),
        [
            pytest.param(
                list_multiple_dependencies_factory,
                [_service, _another_service],
                id="multiple_dependencies",
            ),
            pytest.param(
                list_positional_only_factory,
                [_service, _another_service, _yet_another_service],
                id="positional_only",
            ),
            pytest.param(
                list_positional_only_arg_with_default_factory,
                [_service, None],
                id="positional_only_arg_with_default",
            ),
            pytest.param(
                list_keyword_only_factory,
                [_service, _another_service],
                id="keyword_only",
            ),
            pytest.param(
                list_keyword_arg_with_default_factory,
                [_service, None],
                id="keyword_arg_with_default",
            ),
            pytest.param(
                list_ignores_variadic_args_factory,
                [_service, (), {}],
                id="variadic_args",
            ),
            pytest.param(
                list_string_type_annotation_factory,
                [_service],
                id="string_type_annotation",
            ),
        ],
    )
    def test_autowire_function_signature_shapes(
        self, registry, container, func, expected
    ):
        """
        autowire resolves dependencies for supported function signatures.
        """
        registry.register_factory(list, autowire(func))

        result = container.get(list)

        assert expected == result

    def test_autowire_arg_required(self, registry, container):
        """
        autowire raises ServiceNotFoundError if a required keyword
        parameter cannot be found in the container.
        """

        @autowire
        def func(svc: Service, required: str): ...

        registry.register_factory(tuple, func)

        with pytest.raises(ServiceNotFoundError):
            container.get(tuple)

    @pytest.mark.parametrize("special_type", SPECIAL_TYPE_CASES)
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


class TestAutowireClass:
    @pytest.mark.parametrize(
        ("service_cls", "expected"),
        [
            pytest.param(SingleService, SingleService(_service), id="single"),
            pytest.param(
                MultipleServices,
                MultipleServices(_service, _another_service),
                id="multiple",
            ),
            pytest.param(
                KeywordOnlyServices,
                KeywordOnlyServices(
                    svc=_service,
                    another=_another_service,
                ),
                id="keyword_only",
            ),
            pytest.param(
                PositionalOnlyServices,
                PositionalOnlyServices(
                    _service,
                    _another_service,
                    _yet_another_service,
                ),
                id="positional_only",
            ),
            pytest.param(
                KeywordArgWithDefault,
                KeywordArgWithDefault(_service, None),
                id="keyword_arg_with_default",
            ),
            pytest.param(
                PositionalOnlyArgWithDefault,
                PositionalOnlyArgWithDefault(_service, None),
                id="positional_only_arg_with_default",
            ),
            pytest.param(
                VariadicArgs,
                VariadicArgs(_service),
                id="variadic_args",
            ),
            pytest.param(
                InitVarService,
                InitVarService(_service, _another_service),
                id="initvar",
            ),
            pytest.param(
                StringAnnotationService,
                StringAnnotationService(_service),
                id="string_type_annotation",
            ),
        ],
    )
    def test_autowire_class_signature_shapes(
        self, registry, container, service_cls, expected
    ):
        """
        autowire resolves dependencies for supported class signatures.
        """

        registry.register_factory(service_cls, autowire(service_cls))

        resolved = container.get(service_cls)

        assert expected == resolved

    @pytest.mark.parametrize("special_type", SPECIAL_TYPE_CASES)
    def test_autowire_class_special_types(
        self, registry, container, special_type
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

    def test_autowire_class_arg_required(self, registry, container):
        """
        autowire raises ServiceNotFoundError if a required class
        constructor parameter cannot be found in the container.
        """

        class MyClass:
            def __init__(self, svc: Service, required: str): ...

        registry.register_factory(MyClass, autowire(MyClass))

        with pytest.raises(ServiceNotFoundError):
            container.get(MyClass)


@pytest.mark.asyncio
class TestAAutowireFunction:
    @pytest.mark.parametrize(
        ("func", "expected"),
        [
            pytest.param(
                async_list_multiple_dependencies_factory,
                [_service, _another_service],
                id="multiple_dependencies",
            ),
            pytest.param(
                async_list_positional_only_factory,
                [_service, _another_service, _yet_another_service],
                id="positional_only",
            ),
            pytest.param(
                async_list_positional_only_arg_with_default_factory,
                [_service, None],
                id="positional_only_arg_with_default",
            ),
            pytest.param(
                async_list_keyword_only_factory,
                [_service, _another_service],
                id="keyword_only",
            ),
            pytest.param(
                async_list_keyword_arg_with_default_factory,
                [_service, None],
                id="keyword_arg_with_default",
            ),
            pytest.param(
                async_list_ignores_variadic_args_factory,
                [_service, (), {}],
                id="variadic_args",
            ),
            pytest.param(
                async_list_string_type_annotation_factory,
                [_service],
                id="string_type_annotation",
            ),
        ],
    )
    async def test_aautowire_function_signature_shapes(
        self, registry, container, func, expected
    ):
        """
        aautowire resolves dependencies for supported function signatures.
        """
        registry.register_factory(list, aautowire(func))

        result = await container.aget(list)

        assert expected == result

    async def test_aautowire_arg_required(self, registry, container):
        """
        aautowire raises ServiceNotFoundError if a required keyword
        parameter cannot be found in the container.
        """

        @aautowire
        async def func(svc: Service, required: str): ...

        registry.register_factory(tuple, func)

        with pytest.raises(ServiceNotFoundError):
            await container.aget(tuple)

    @pytest.mark.parametrize("special_type", SPECIAL_TYPE_CASES)
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


@pytest.mark.asyncio
class TestAAutowireClass:
    @pytest.mark.parametrize(
        ("service_cls", "expected"),
        [
            pytest.param(SingleService, SingleService(_service), id="single"),
            pytest.param(
                MultipleServices,
                MultipleServices(_service, _another_service),
                id="multiple",
            ),
            pytest.param(
                KeywordOnlyServices,
                KeywordOnlyServices(
                    svc=_service,
                    another=_another_service,
                ),
                id="keyword_only",
            ),
            pytest.param(
                PositionalOnlyServices,
                PositionalOnlyServices(
                    _service,
                    _another_service,
                    _yet_another_service,
                ),
                id="positional_only",
            ),
            pytest.param(
                KeywordArgWithDefault,
                KeywordArgWithDefault(_service, None),
                id="keyword_arg_with_default",
            ),
            pytest.param(
                PositionalOnlyArgWithDefault,
                PositionalOnlyArgWithDefault(_service, None),
                id="positional_only_arg_with_default",
            ),
            pytest.param(
                VariadicArgs,
                VariadicArgs(_service),
                id="variadic_args",
            ),
            pytest.param(
                InitVarService,
                InitVarService(_service, _another_service),
                id="initvar",
            ),
            pytest.param(
                StringAnnotationService,
                StringAnnotationService(_service),
                id="string_type_annotation",
            ),
        ],
    )
    async def test_aautowire_class_signature_shapes(
        self, registry, container, service_cls, expected
    ):
        """
        aautowire resolves dependencies for supported class signatures.
        """

        registry.register_factory(service_cls, aautowire(service_cls))

        resolved = await container.aget(service_cls)

        assert expected == resolved

    @pytest.mark.parametrize("special_type", SPECIAL_TYPE_CASES)
    async def test_aautowire_class_special_types(
        self, registry, container, special_type
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

    async def test_aautowire_class_arg_required(self, registry, container):
        """
        aautowire raises ServiceNotFoundError if a required class
        constructor parameter cannot be found in the container.
        """

        class MyClass:
            def __init__(self, svc: Service, required: str): ...

        registry.register_factory(MyClass, aautowire(MyClass))

        with pytest.raises(ServiceNotFoundError):
            await container.aget(MyClass)
