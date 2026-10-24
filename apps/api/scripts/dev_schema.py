"""One-off helper: build a throwaway copy of the schema with Alembic, then run the tests.

Usage (from apps/api):
    uv run --env-file ../../.env python scripts/dev_schema.py up    # create + migrate
    uv run --env-file ../../.env python scripts/dev_schema.py test  # run tests against it
    uv run --env-file ../../.env python scripts/dev_schema.py drop  # drop it

Kept outside tests/ so pytest does not collect it.
"""

import os
import subprocess
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
from sqlalchemy import create_engine, text

from app.core.config import DATABASE_URL

SCHEMA_NAME = os.getenv("DEV_SCHEMA") or f"pytest_{os.getpid()}"
API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def with_schema(url: str, schema: str | None) -> str:
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "options"]
    if schema:
        query.append(("options", f"-csearch_path={schema}"))
    return urlunsplit(parts._replace(query=urlencode(query)))


def admin(schema: str) -> str:
    """URL with the schema stripped so CREATE/DROP SCHEMA can run."""
    return with_schema(DATABASE_URL, None)


def main(action: str) -> int:
    if not DATABASE_URL:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2

    engine = create_engine(admin(SCHEMA_NAME), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA_NAME}"'))
    env = {**os.environ, "DATABASE_URL": with_schema(DATABASE_URL, SCHEMA_NAME)}

    try:
        if action in {"up", "all"}:
            subprocess.run(["alembic", "upgrade", "head"], check=True, cwd=API_DIR, env=env)
        if action in {"test", "all"}:
            code = pytest.main(["tests/test_db_schema.py", "-q", "--no-header"], plugins=[])
            return code
        print(f"schema ready: {SCHEMA_NAME}\nDATABASE_URL for this schema:\n{env['DATABASE_URL']}")
        return 0
    finally:
        if action == "drop":
            with engine.connect() as conn:
                conn.execute(text(f'DROP SCHEMA IF EXISTS "{SCHEMA_NAME}" CASCADE'))
            engine.dispose()
            print(f"dropped schema {SCHEMA_NAME}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "up"))
