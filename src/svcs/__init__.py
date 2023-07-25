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
    "ServiceNotFoundError",
    "ServicePing",
    "exceptions",
]

try:
    from . import flask  # noqa: F401
except ImportError:
    __all__.append("flask")
