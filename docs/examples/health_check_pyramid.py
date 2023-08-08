from __future__ import annotations

import json

from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_config


@view_config(route_name="healthy")
def healthy_view(request: Request) -> Response:
    ok: list[str] = []
    failing: list[dict[str, str]] = []
    status = 200

    for svc in request.svcs.get_pings():
        try:
            svc.ping()
            ok.append(svc.name)
        except Exception as e:
            failing.append({svc.name: repr(e)})
            status = 500

    return Response(
        content_type="application/json",
        status=status,
        body=json.dumps({"ok": ok, "failing": failing}).encode("ascii"),
    )
