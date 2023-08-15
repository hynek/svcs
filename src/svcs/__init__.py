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


# Make nicer public names.
__locals = locals()
for __name in __all__:
    if not __name.startswith("__") and not __name.islower():
        __locals[__name].__module__ = "svcs"
del __locals
del __name  # pyright: ignore[reportUnboundVariable]
