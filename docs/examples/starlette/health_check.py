from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

import svcs


async def healthy(request: Request) -> JSONResponse:
    """
    Ping all external services.
    """
    ok: list[str] = []
    failing: dict[str, str] = {}
    code = 200

    for svc in svcs.flask.get_pings():
        try:
            svc.ping()
            ok.append(svc.name)
        except Exception as e:
            failing[svc.name] = repr(e)
            code = 500

    return JSONResponse(
        content={"ok": ok, "failing": failing}, status_code=code
    )
