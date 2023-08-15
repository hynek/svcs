# Changelog

All notable changes to this project will be documented in this file.

The format is based on [*Keep a Changelog*](https://keepachangelog.com/en/1.0.0/) and this project adheres to [*Calendar Versioning*](https://calver.org/).

The **first number** of the version is the year.
The **second number** is incremented with each release, starting at 1 for each year.
The **third number** is for emergencies when we need to start branches for older releases.

You can find our backwards-compatibility policy [here](https://github.com/hynek/svcs/blob/main/.github/SECURITY.md).

<!-- changelog follows -->


## [23.17.0](https://github.com/hynek/svcs/compare/23.16.0...23.17.0) - 2023-08-15

### Added

- FastAPI integration.
  [#20](https://github.com/hynek/svcs/pull/30)


## [23.16.0](https://github.com/hynek/svcs/compare/23.15.0...23.16.0) - 2023-08-14

### Added

- *enter* keyword argument to all `register_(value|factory)()`.
  It prevents *svcs* from entering context managers if the factory returns one.
  This is useful for context managers like database transactions that you want to start manually.

- Services acquired using `aget()` now also can receive the current container if they take one argument that is named `svcs_container` or that is annotated as being `svcs.Container` and has any name.


## [23.15.0](https://github.com/hynek/svcs/compare/23.14.0...23.15.0) - 2023-08-14

### Added

- A `ResourceWarning` is now raised when a container or a registry are garbage-collected with pending cleanups.


### Changed

- Cleanups for services are internally context managers now.
  For your convenience, if you pass an (async) generator function for a factory, the registry will automatically wrap it for you into an (async) context manager.
  [#29](https://github.com/hynek/svcs/pull/29)

- Pyramid: `svcs.pyramid.get()` now takes a Pyramid request as the first argument.
  `svcs.pyramid.get_pings()` also doesn't look at thread locals anymore.
  If you still want to use thread locals, you can use `svcs.pyramid.from_svcs(None)` to obtain the currently active container.

- Flask: `replace_(value|factory)()` is now called `overwrite_(value|factory())` to be consistent with the docs lingo.
  They also completely reset the instantiation cache now (practically speaking: they close the container).


### Removed

- `svcs.Container.forget_about()`.
  It doesn't make any sense in a world of recursive dependencies.
  Just reset the container using `svcs.Container.(a)close()`.


## [23.14.0](https://github.com/hynek/svcs/compare/23.13.0...23.14.0) - 2023-08-11

### Added

- AIOHTTP: missing `aget_abstract()` function.
- Pyramid: missing `get_pings()` function.


## [23.13.0](https://github.com/hynek/svcs/compare/23.12.0...23.13.0) - 2023-08-11

### Added

- AIOHTTP integration.


## [23.12.0](https://github.com/hynek/svcs/compare/23.11.0...23.12.0) - 2023-08-09

### Added

- *svcs* now logs registrations at debug level along with a stacktrace.
  So if you ever get confused where your factories are coming from, set the log level to debug and trace your registrations!


### Changed

- Ooof.
  It's obvious in hindsight, but accessing anything directly on a request object like in the `request.svcs.get()` examples erases type information and everything becomes a big soup of `Any`.

  Therefore, we've added a new "best practice" for integrations to have a `svcs_from()` function that extracts containers from request objects (or from thread locals in the case of Flask).


## [23.11.0](https://github.com/hynek/svcs/compare/23.10.0...23.11.0) - 2023-08-08

### Changed

- Factory results of None are now treated like every other result and cached.
  [#22](https://github.com/hynek/svcs/pull/22)

- Calling `Container.get()` on a service that has an async factory now raises a `TypeError`.
  [#21](https://github.com/hynek/svcs/pull/21)


### Added

- API reference docs!

- A **huge** [glossary](https://svcs.hynek.me/en/stable/glossary.html) that should have been a book.
  [#20](https://github.com/hynek/svcs/pull/20)


## [23.10.0](https://github.com/hynek/svcs/compare/23.9.0...23.10.0) - 2023-08-07

### Added

- Proper documentation at <https://svcs.hynek.me/>!
  I guess it's getting serious.
  [#17](https://github.com/hynek/svcs/pull/17)

- Pyramid integration.

  Please note that not all integrations will be shipped with *svcs* proper once it is stable.
  Some will be moved to separate packages and Pyramid is a prime contender for that.


## [23.9.0](https://github.com/hynek/svcs/compare/23.8.0...23.9.0) - 2023-08-06

### Changed

- `Container.get()` and `Container.aget()` now have type hints that only work with concrete classes but allow for type checking without repeating yourself.
  If you want to use abstract classes like `typing.Protocol` or ABCs, you can use `Container.get_abstract()` and `Container.aget_abstract()` instead.


### Added

- `Container.get_abstract()` and `Container.aget_abstract()`.
  They behave like `Container.get()` and `Container.aget()` before.

- It is now possible to check if a service type is registered with a `Registry` by using `in`.

- It is now possible to check if a service type has a cached instance within a `Container` by using `in`.

- `Registry` and `Container` are now also an (async) context managers that call `close()` / `aclose()` on exit automatically.


## [23.8.0](https://github.com/hynek/svcs/compare/23.7.0...23.8.0) - 2023-08-04

### Added

- It's now possible to request multiple services at once by passing multiple types to `Container.get()` and `Container.aget()`.
  [#15](https://github.com/hynek/svcs/pull/15)


## [23.7.0](https://github.com/hynek/svcs/compare/23.6.0...23.7.0) - 2023-08-02

### Added

- Factories now may take a parameter called `svcs_container` or that is annotated to be `svcs.Container`.
  In this case the factory will receive the current container as a first positional argument.
  This allows for recursive factories without global state.
  [#10](https://github.com/hynek/svcs/pull/10)


## [23.6.0](https://github.com/hynek/svcs/compare/23.5.0...23.6.0) - 2023-07-31

### Changed

- Renamed `Container.forget_service_type()` to `Container.forget_about()`.


### Fixed

- `svcs.flask.init_app()`'s type hints now take into account custom `flask.Flask` subclasses.


## [23.5.0](https://github.com/hynek/svcs/compare/23.4.0...23.5.0) - 2023-07-26

### Added

- Registered factory/value clean up!
  It is now possible to register an `on_registry_close` hook that is called once the `Registry`'s `(a)close()` method is called.


## [23.4.0](https://github.com/hynek/svcs/compare/23.3.0...23.4.0) - 2023-07-24

### Changed

- Renamed from *svc-reg* to *svcs*.
  Sadly the more obvious names are all taken.


## [23.3.0](https://github.com/hynek/svcs/compare/23.2.0...23.3.0) - 2023-07-20

### Added

- Async method `Container.aget()`.
  This was necessary for generator-based cleanups.
  It works with sync factories too, so you can use it universally in async code.
- Async method `ServicePing.aping()`.
  It works with sync factories and pings too, so you can use it universally in async code.
  [#4](https://github.com/hynek/svcs/pull/4)


### Changed

- Switched the cleanup mechanism from passing a function to allowing the factory to be a generator that yields the service and can clean up after the `yield`.
  Just like Pytest fixtures.
  [#3](https://github.com/hynek/svcs/pull/3)


## [23.2.0](https://github.com/hynek/svcs/compare/23.1.0...23.2.0) - 2023-07-13

### Changed

- `Container.cleanup()` and `Container.acleanup` have been renamed to `close()` and `aclose()` respectively.
- The clean up methods are now more resilient by catching and logging exceptions at `warning` level.
  That means that if the first clean up method fails, the second one will still be called.
- `svcs.flask.register_(factory|value)` now take the current Flask application as first argument.
  The old behavior moved to `svcs.flask.replace_(factory|value)`.

  The former requires no application context (and thusly be used in `init_app()`-style initializers) while the latter *does* require an application context and can be used to "monkey-patch" an existing application in tests.


## [23.1.0](https://github.com/hynek/svcs/tree/23.1.0) - 2023-07-12

- Initial release.
