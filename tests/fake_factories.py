# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio

from contextlib import asynccontextmanager, contextmanager

from tests.ifaces import (
    AnotherService,
    Service,
    UnregisteredService,
    YetAnotherService,
)


def int_factory():
    return 42


def str_gen_factory():
    yield "foo"


@contextmanager
def bool_cm_factory():
    yield True


async def async_int_factory():
    await asyncio.sleep(0)
    return 42


async def async_str_gen_factory():
    await asyncio.sleep(0)
    yield str(42)
    await asyncio.sleep(0)


@asynccontextmanager
async def async_bool_cm_factory():
    await asyncio.sleep(0)
    yield True


def list_multiple_dependencies_factory(
    svc: Service, another: AnotherService
) -> list:
    return [svc, another]


def list_positional_only_factory(
    svc: Service,
    another: AnotherService,
    /,
    yet_another: YetAnotherService,
) -> list:
    return [svc, another, yet_another]


def list_positional_only_arg_with_default_factory(
    svc: Service, optional: UnregisteredService | None = None, /
) -> list:
    return [svc, optional]


def list_keyword_only_factory(
    *, svc: Service, another: AnotherService
) -> list:
    return [svc, another]


def list_keyword_arg_with_default_factory(
    svc: Service, optional: UnregisteredService | None = None
) -> list:
    return [svc, optional]


def list_string_type_annotation_factory(svc: "Service") -> list:
    return [svc]


def list_ignores_variadic_args_factory(
    svc: Service, *args: str, **kwargs: int
) -> list:
    return [svc, args, kwargs]


async def async_list_multiple_dependencies_factory(
    svc: Service, another: AnotherService
) -> list:
    return [svc, another]


async def async_list_positional_only_factory(
    svc: Service,
    another: AnotherService,
    /,
    yet_another: YetAnotherService,
) -> list:
    return [svc, another, yet_another]


async def async_list_positional_only_arg_with_default_factory(
    svc: Service, optional: UnregisteredService | None = None, /
) -> list:
    return [svc, optional]


async def async_list_keyword_only_factory(
    *, svc: Service, another: AnotherService
) -> list:
    return [svc, another]


async def async_list_keyword_arg_with_default_factory(
    svc: Service, optional: UnregisteredService | None = None
) -> list:
    return [svc, optional]


async def async_list_string_type_annotation_factory(
    svc: "Service",
) -> list:
    return [svc]


async def async_list_ignores_variadic_args_factory(
    svc: Service, *args: str, **kwargs: int
) -> list:
    return [svc, args, kwargs]
