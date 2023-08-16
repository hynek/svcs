from unittest.mock import Mock

import pytest

from starlette.testclient import TestClient

from simple_starlette_app import Database, app, lifespan


@pytest.fixture(name="client")
def _client():
    with TestClient(app) as client:
        yield client


def test_db_goes_boom(client):
    """
    Database errors are handled gracefully.
    """

    # IMPORTANT: Overwriting must happen AFTER the app is ready!
    db = Mock(spec_set=Database)
    db.get_user.side_effect = Exception("boom")
    lifespan.registry.register_value(Database, db)

    resp = client.get("/users/42")

    assert {"oh no": "boom"} == resp.json()
