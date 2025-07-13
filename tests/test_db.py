import os
import asyncio
import pytest
from ai_companion.db import DBsqlite

@pytest.mark.asyncio
async def test_add_and_get_history(tmp_path):
    db_file = tmp_path / "test.db"
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.schema")
    with open(schema_path) as f:
        schema = f.read()
    db = DBsqlite(str(db_file), schema)
    await db.connect()
    await db.register_user(type("U", (), {"id": 1, "username": "u", "first_name": "f", "last_name": "l"})())
    await db.add_history(1, "user", "hello")
    history = await db.get_history(1)
    assert history and history[-1]["content"] == "hello"
    await db.clear_history(1)
    history = await db.get_history(1)
    assert history == []
    await db.close()

