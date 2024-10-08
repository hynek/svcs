from __future__ import annotations

import flask

import svcs


bp = flask.Blueprint("instrumentation", __name__)


@bp.get("healthy")
def healthy() -> flask.ResponseValue:
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

    return {"ok": ok, "failing": failing}, code
