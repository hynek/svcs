# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import sys

from contextlib import suppress

from . import exceptions
from ._autowire import aautowire, autowire
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
    "aautowire",
    "autowire",
    "exceptions",
]

if sys.version_info >= (3, 15):
    # Relative imports are keyed on the package, not on the submodule.
    __lazy_modules__ = ["svcs"]

    from . import aiohttp as aiohttp
    from . import fastapi as fastapi
    from . import flask as flask
    from . import starlette as starlette
else:
    with suppress(ImportError):
        from . import aiohttp as aiohttp

    with suppress(ImportError):
        from . import fastapi as fastapi

    with suppress(ImportError):
        from . import flask as flask

    with suppress(ImportError):
        from . import starlette as starlette
