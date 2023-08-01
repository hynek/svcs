# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from . import exceptions
from ._core import (
    Container,
    RegisteredService,
    Registry,
    ServicePing,
)


__all__ = [
    "Container",
    "RegisteredService",
    "Registry",
    "ServicePing",
    "exceptions",
]

try:
    from . import flask  # noqa: F401
except ImportError:
    __all__.append("flask")


# Make nicer public names.
__locals = locals()
for __name in __all__:
    if not __name.startswith("__") and not __name.islower():
        __locals[__name].__module__ = "svcs"
del __locals
del __name
