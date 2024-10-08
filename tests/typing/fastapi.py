# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

import svcs


@svcs.fastapi.lifespan
async def lifespan(
    app: FastAPI, registry: svcs.Registry
) -> AsyncGenerator[dict[str, object], None]:
    yield {}


reg: svcs.Registry = lifespan.registry


@svcs.fastapi.lifespan
async def lifespan2(
    app: FastAPI, registry: svcs.Registry
) -> AsyncGenerator[None, None]:
    yield


@svcs.fastapi.lifespan
@asynccontextmanager
async def lifespan3(
    app: FastAPI, registry: svcs.Registry
) -> AsyncGenerator[dict[str, object], None]:
    yield {}


@svcs.fastapi.lifespan
@asynccontextmanager
async def lifespan4(
    app: FastAPI, registry: svcs.Registry
) -> AsyncGenerator[None, None]:
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def view(
    services: Annotated[svcs.Container, Depends(svcs.fastapi.container)],
) -> JSONResponse:
    x: int = services.get(int)

    return JSONResponse({}, 200)


@app.get("/")
async def view2(services: svcs.fastapi.DepContainer) -> JSONResponse:
    x: int = services.get(int)

    return JSONResponse({}, 200)
