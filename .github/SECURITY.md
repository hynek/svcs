# Security Policy

## Supported Versions

We're following [*CalVer*](https://calver.org) with generous backwards-compatibility guarantees.
Therefore we only support the latest version.

That said, you shouldn't be afraid to upgrade if you're only using our documented public APIs and pay attention to `DeprecationWarning`s.
Whenever there is a need to break compatibility, it is announced in the changelog and raises a `DeprecationWarning` for a year (if possible) before it's finally really broken.

> [!WARNING]
> There are **two** exception:
>
> 1. We reserve the right to **remove framework integrations** at any time *without prior notice* to ease the maintenance burden.
>    We *will* try to put them as separate packages on PyPI if we do so.
>
> 2. APIs may be marked as *provisional*.
>    They are not guaranteed to be stable and may change or be removed without prior notice.


## Reporting a Vulnerability

If you think you found a vulnerability, please use [GitHub's security advisory form](https://github.com/hynek/svcs/security/advisories/new), or email Hynek Schlawack at <hs@ox.cx>.
