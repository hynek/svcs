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
    from . import aiohttp
except ImportError:
    __all__ += ["aiohttp"]

try:
    from . import fastapi
except ImportError:
    __all__ += ["fastapi"]

try:
    from . import flask
except ImportError:
    __all__ += ["flask"]

try:
    from . import pyramid
except ImportError:
    __all__ += ["pyramid"]

try:
    from . import starlette
except ImportError:
    __all__ += ["starlette"]
