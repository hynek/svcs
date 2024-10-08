from __future__ import annotations

import json

from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_config

import svcs


@view_config(route_name="healthy")
def healthy_view(request: Request) -> Response:
    """
    Ping all external services.
    """
    ok: list[str] = []
    failing: dict[str, str] = {}
    status = 200

    for svc in svcs.pyramid.get_pings(request):
        try:
            svc.ping()
            ok.append(svc.name)
        except Exception as e:
            failing[svc.name] = repr(e)
            status = 500

    return Response(
        content_type="application/json",
        status=status,
        body=json.dumps({"ok": ok, "failing": failing}).encode("ascii"),
    )
