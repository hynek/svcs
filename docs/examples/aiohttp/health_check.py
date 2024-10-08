from __future__ import annotations

from aiohttp.web import Request, Response, json_response

import svcs


async def healthy_view(request: Request) -> Response:
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

    return json_response({"ok": ok, "failing": failing}, status=code)
