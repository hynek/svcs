from __future__ import annotations

import os

from typing import AsyncGenerator

from fastapi import Depends, FastAPI
from typing_extensions import Annotated

import svcs


config = {"db_url": os.environ.get("DB_URL", "sqlite:///:memory:")}


class Database:
    @classmethod
    async def connect(cls, db_url: str) -> Database:
        ...
        return Database()

    async def get_user(self, user_id: int) -> dict[str, str]:
        return {}  # TODO


@svcs.fastapi.lifespan
async def lifespan(
    app: FastAPI, registry: svcs.Registry
) -> AsyncGenerator[dict[str, object], None]:
    async def connect_to_db() -> Database:
        return await Database.connect(config["db_url"])

    registry.register_factory(Database, connect_to_db)

    yield {"your": "other stuff"}


app = FastAPI(lifespan=lifespan)


@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    svcs: Annotated[svcs.Container, Depends(svcs.fastapi.container)],
) -> dict:
    db = await svcs.aget(Database)

    try:
        return {"data": await db.get_user(user_id)}
    except Exception as e:
        return {"oh no": e.args[0]}
