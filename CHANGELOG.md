# Changelog

All notable changes to this project will be documented in this file.

The format is based on [*Keep a Changelog*](https://keepachangelog.com/en/1.0.0/) and this project adheres to [*Calendar Versioning*](https://calver.org/).

The **first number** of the version is the year.
The **second number** is incremented with each release, starting at 1 for each year.
The **third number** is for emergencies when we need to start branches for older releases.

You can find our backwards-compatibility policy [here](https://github.com/hynek/svcs/blob/main/.github/SECURITY.md).

<!-- changelog follows -->


## [23.4.0](https://github.com/hynek/svcs/compare/23.3.0...23.4.0) - 2023-07-24

### Changed

- Renamed from *reg-svc* to *svcs*.
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

- Switched the cleanup mechanism from passing a function to allowing the factory to be a generator that yields the resource and can clean up after the `yield`.
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
