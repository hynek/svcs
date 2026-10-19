# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Benchmarks for the hot paths of svcs: registering services, acquiring them
from containers (cold and cached), cleanups, autowiring, and pings.

Run with ``pytest benchmarks --codspeed``.
"""

import asyncio

from contextlib import asynccontextmanager, contextmanager

import pytest

import svcs


class Database:
    pass


class Cache:
    pass


class Mailer:
    pass


class Session:
    def __init__(self, db: Database, cache: Cache) -> None:
        self.db = db
        self.cache = cache


class Handler:
    def __init__(self, session: Session, mailer: Mailer) -> None:
        self.session = session
        self.mailer = mailer


# Many distinct types to exercise registries of realistic size.
SERVICE_TYPES = [type(f"Service{i}", (), {}) for i in range(100)]


@contextmanager
def database_factory():
    yield Database()


@asynccontextmanager
async def async_database_factory():
    yield Database()


async def async_cache_factory():
    return Cache()


def session_factory(container: svcs.Container) -> Session:
    return Session(*container.get(Database, Cache))


@pytest.fixture(name="registry")
def _registry():
    reg = svcs.Registry()
    reg.register_factory(Database, database_factory)
    reg.register_factory(Cache, Cache)
    reg.register_value(Mailer, Mailer())
    reg.register_factory(Session, session_factory)
    for t in SERVICE_TYPES:
        reg.register_factory(t, t)

    yield reg

    reg.close()


@pytest.fixture(name="event_loop")
def _event_loop():
    loop = asyncio.new_event_loop()

    yield loop

    loop.close()


def test_register_factories(benchmark):
    """
    Build a registry with 100 factories and close it.
    """

    @benchmark
    def _():
        reg = svcs.Registry()
        for t in SERVICE_TYPES:
            reg.register_factory(t, t)
        reg.close()


def test_register_values(benchmark):
    """
    Build a registry with 100 values and close it.
    """
    values = [t() for t in SERVICE_TYPES]

    @benchmark
    def _():
        reg = svcs.Registry()
        for t, v in zip(SERVICE_TYPES, values, strict=True):
            reg.register_value(t, v)
        reg.close()


def test_get_single_cold(benchmark, registry):
    """
    Typical request: fresh container, acquire one service, close.
    """

    @benchmark
    def _():
        with svcs.Container(registry) as con:
            con.get(Cache)


def test_get_cached(benchmark, registry):
    """
    Repeatedly acquire an already instantiated service.
    """
    con = svcs.Container(registry)
    con.get(Cache)

    @benchmark
    def _():
        for _ in range(100):
            con.get(Cache)

    con.close()


def test_get_multiple(benchmark, registry):
    """
    Acquire several services in one call, including one that takes the
    container and one that is a context manager that needs cleanup.
    """

    @benchmark
    def _():
        with svcs.Container(registry) as con:
            con.get(Session, Mailer, Database, Cache)


def test_get_many_types(benchmark, registry):
    """
    Acquire 100 distinct services from a fresh container.
    """

    @benchmark
    def _():
        with svcs.Container(registry) as con:
            for t in SERVICE_TYPES:
                con.get(t)


def test_container_cleanup(benchmark, registry):
    """
    Enter and clean up many context manager-based services.
    """

    @benchmark
    def _():
        con = svcs.Container(registry)
        for _ in range(50):
            con.get(Database)
            con.close()


def test_local_registry(benchmark, registry):
    """
    Register container-local overrides and acquire them.
    """

    @benchmark
    def _():
        with svcs.Container(registry) as con:
            con.register_local_value(Cache, Cache())
            con.register_local_factory(Database, Database)
            con.get(Cache, Database, Mailer)


def test_autowire(benchmark, registry):
    """
    Resolve a two-level dependency graph through autowired factories.
    """
    registry.register_factory(Session, svcs.autowire(Session))
    registry.register_factory(Handler, svcs.autowire(Handler))

    @benchmark
    def _():
        with svcs.Container(registry) as con:
            con.get(Handler)


def test_get_pings(benchmark, registry):
    """
    Collect and run health checks.
    """
    for t in SERVICE_TYPES[:20]:
        registry.register_factory(t, t, ping=lambda _: None)

    @benchmark
    def _():
        with svcs.Container(registry) as con:
            for ping in con.get_pings():
                ping.ping()


def test_aget(benchmark, registry, event_loop):
    """
    Acquire async and sync services asynchronously and clean them up.
    """
    registry.register_factory(Database, async_database_factory)
    registry.register_factory(Cache, async_cache_factory)

    async def acquire():
        async with svcs.Container(registry) as con:
            await con.aget(Database, Cache, Mailer)

    benchmark(lambda: event_loop.run_until_complete(acquire()))


def test_aautowire(benchmark, registry, event_loop):
    """
    Resolve dependencies through an async autowired factory.
    """
    registry.register_factory(Cache, async_cache_factory)
    registry.register_factory(Session, svcs.aautowire(Session))

    async def acquire():
        async with svcs.Container(registry) as con:
            await con.aget(Session)

    benchmark(lambda: event_loop.run_until_complete(acquire()))
