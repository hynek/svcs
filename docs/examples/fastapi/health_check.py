from __future__ import annotations

from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

import svcs


@svcs.fastapi.lifespan
async def lifespan(
    app: FastAPI, registry: svcs.Registry
) -> AsyncGenerator[dict[str, object], None]:
    # Register your services here using the *registry* argument.

    yield {"your": "other state"}


app = FastAPI(lifespan=lifespan)

##############################################################################


@app.get("/healthy")
async def healthy(services: svcs.fastapi.DepContainer) -> JSONResponse:
    """
    Ping all external services.
    """
    ok: list[str] = []
    failing: list[dict[str, str]] = []
    code = 200

    for svc in services.get_pings():
        try:
            await svc.aping()
            ok.append(svc.name)
        except Exception as e:
            failing.append({svc.name: repr(e)})
            code = 500

    return JSONResponse(
        content={"ok": ok, "failing": failing}, status_code=code
    )
