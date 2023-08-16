from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

import svcs


app = FastAPI(...)


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
