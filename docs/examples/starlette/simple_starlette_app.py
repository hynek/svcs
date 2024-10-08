from __future__ import annotations

import os

from collections.abc import AsyncGenerator

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

import svcs


config = {"db_url": os.environ.get("DB_URL", "sqlite:///:memory:")}


class Database:
    @classmethod
    async def connect(cls, db_url: str) -> Database:
        # ...
        return Database()

    async def get_user(self, user_id: int) -> dict[str, str]:
        return {}  # not interesting here


async def get_user(request: Request) -> JSONResponse:
    db = await svcs.starlette.aget(request, Database)

    try:
        return JSONResponse(
            {"data": await db.get_user(request.path_params["user_id"])}
        )
    except Exception as e:
        return JSONResponse({"oh no": e.args[0]})


@svcs.starlette.lifespan
async def lifespan(
    app: Starlette, registry: svcs.Registry
) -> AsyncGenerator[dict[str, object], None]:
    async def connect_to_db() -> Database:
        return await Database.connect(config["db_url"])

    registry.register_factory(Database, connect_to_db)

    yield {"your": "other stuff"}


app = Starlette(
    lifespan=lifespan,
    middleware=[Middleware(svcs.starlette.SVCSMiddleware)],
    routes=[Route("/users/{user_id}", get_user)],
)
