# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Tests for svcs.autowire() and svcs.aautowire().
"""

import functools
import textwrap

from contextlib import asynccontextmanager, contextmanager
from typing import Annotated, NewType

import pytest

from svcs import Container, aautowire, autowire
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
"""
Special Python types that autowire should support when resolving dependencies.
"""


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

    def test_autowire_does_not_mask_nested_error(self, registry, container):
        """
        A ServiceNotFoundError raised while building a *registered*
        dependency is propagated, not masked by the parameter's own
        default.
        """

        class Missing: ...

        class Database:
            def __init__(self, missing: Missing) -> None: ...

        fallback = object()

        def build(db: Database = fallback) -> tuple: ...

        registry.register_factory(Database, autowire(Database))
        registry.register_factory(tuple, autowire(build))

        with pytest.raises(ServiceNotFoundError) as ei:
            container.get(tuple)

        assert Missing is ei.value.args[0]

    def test_autowire_unannotated_required_raises(self, registry, container):
        """
        autowire raises a TypeError for a required parameter without a type
        annotation, since there is nothing to resolve it by.
        """

        @autowire
        def build(svc: Service, mystery) -> tuple: ...

        registry.register_factory(tuple, build)

        with pytest.raises(TypeError, match="mystery"):
            container.get(tuple)

    def test_autowire_unannotated_with_default_uses_default(
        self, registry, container
    ):
        """
        An unannotated parameter with a default keeps that default.
        """

        @autowire
        def build(svc: Service, mystery=42) -> tuple:
            return (svc, mystery)

        registry.register_factory(tuple, build)

        assert (_service, 42) == container.get(tuple)

    def test_autowire_rejects_generator_factories(self):
        """
        autowire rejects bare generator and async generator factories at
        decoration time, because their cleanup would be lost.
        """

        def gen_factory(svc: Service):
            yield svc

        async def agen_factory(svc: Service):
            yield svc

        with pytest.raises(TypeError, match=r"contextlib\.contextmanager"):
            autowire(gen_factory)

        with pytest.raises(
            TypeError, match=r"contextlib\.asynccontextmanager"
        ):
            autowire(agen_factory)

    def test_autowire_context_manager_cleanup(self, registry):
        """
        A factory decorated with @contextlib.contextmanager is autowired and
        its cleanup runs when the container is closed.
        """
        has_cleaned_up = False

        @contextmanager
        def factory(svc: Service):
            nonlocal has_cleaned_up

            yield ("conn", svc)

            has_cleaned_up = True

        registry.register_factory(tuple, autowire(factory))

        with Container(registry) as container:
            assert ("conn", _service) == container.get(tuple)

        assert has_cleaned_up

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

    def test_autowire_sees_through_wraps_decorator(self, registry, container):
        """
        autowire follows __wrapped__, so a factory behind a pass-through
        functools.wraps decorator is autowired from the wrapped signature.
        """

        def logging_decorator(f):
            @functools.wraps(f)
            def inner(*args, **kwargs):
                return f(*args, **kwargs)

            return inner

        @logging_decorator
        def build(svc: Service, another: AnotherService) -> tuple:
            return (svc, another)

        registry.register_factory(tuple, autowire(build))

        assert (_service, _another_service) == container.get(tuple)

    def test_autowire_resolves_forward_reference_at_call_time(
        self, registry, container
    ):
        """
        autowire resolves annotations lazily, when the factory is first
        called.

        A string annotation and other forward references don't fail at import
        time and resolve once everything is defined.
        """
        ns: dict[str, object] = {}
        exec(  # noqa: S102
            textwrap.dedent(
                """
                import svcs

                @svcs.autowire
                def make_holder(dep: "Later") -> tuple:
                    return ("holder", dep)

                class Later:
                    pass
                """
            ),
            ns,
        )

        later = ns["Later"]()
        registry.register_value(ns["Later"], later)
        registry.register_factory(tuple, ns["make_holder"])

        assert ("holder", later) == container.get(tuple)

    def test_autowire_without_signature_raises(self, registry, container):
        """
        autowire raises a TypeError when the callable has no introspectable
        signature.
        """
        registry.register_factory(int, autowire(int))

        with pytest.raises(TypeError, match="signature"):
            container.get(int)

    def test_autowire_signature_reused_across_containers(self, registry):
        """
        The resolved signature is cached, so the same autowired factory
        can be reused across multiple containers.
        """
        registry.register_factory(SingleService, autowire(SingleService))

        with Container(registry) as c1:
            first = c1.get(SingleService)
        with Container(registry) as c2:
            second = c2.get(SingleService)

        assert SingleService(_service) == first
        assert SingleService(_service) == second


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

    async def test_aautowire_does_not_mask_nested_error(
        self, registry, container
    ):
        """
        A ServiceNotFoundError raised while building a *registered*
        dependency is propagated, not masked by the parameter's own
        default.
        """

        class Missing: ...

        class Database:
            def __init__(self, missing: Missing) -> None: ...

        fallback = object()

        def build(db: Database = fallback) -> tuple: ...

        registry.register_factory(Database, aautowire(Database))
        registry.register_factory(tuple, aautowire(build))

        with pytest.raises(ServiceNotFoundError) as ei:
            await container.aget(tuple)

        assert Missing is ei.value.args[0]

    async def test_aautowire_unannotated_required_raises(
        self, registry, container
    ):
        """
        aautowire raises a TypeError for a required parameter without a type
        annotation, since there is nothing to resolve it by.
        """

        @aautowire
        async def build(svc: Service, mystery) -> tuple: ...

        registry.register_factory(tuple, build)

        with pytest.raises(TypeError, match="mystery"):
            await container.aget(tuple)

    async def test_aautowire_unannotated_with_default_uses_default(
        self, registry, container
    ):
        """
        An unannotated parameter with a default keeps that default.
        """

        @aautowire
        async def build(svc: Service, mystery=42) -> tuple:
            return (svc, mystery)

        registry.register_factory(tuple, build)

        assert (_service, 42) == await container.aget(tuple)

    async def test_aautowire_rejects_generator_factories(self):
        """
        aautowire rejects bare generator and async generator factories at
        decoration time, because their cleanup would be lost.
        """

        def gen_factory(svc: Service):
            yield svc

        async def agen_factory(svc: Service):
            yield svc

        with pytest.raises(TypeError, match=r"contextlib\.contextmanager"):
            aautowire(gen_factory)

        with pytest.raises(
            TypeError, match=r"contextlib\.asynccontextmanager"
        ):
            aautowire(agen_factory)

    async def test_aautowire_context_manager_cleanup(self, registry):
        """
        A factory decorated with @contextlib.asynccontextmanager is
        autowired and its cleanup runs when the container is closed.
        """
        cleanups = []

        @asynccontextmanager
        async def factory(svc: Service):
            yield ("conn", svc)
            cleanups.append("closed")

        registry.register_factory(tuple, aautowire(factory))

        async with Container(registry) as container:
            assert ("conn", _service) == await container.aget(tuple)

        assert ["closed"] == cleanups

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
