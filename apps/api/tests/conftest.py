import os

import pytest
from sqlalchemy import create_engine, text

from app.core.config import DATABASE_URL


@pytest.fixture(scope="session")
def db_engine():
    """Engine for the database under test (TEST_DATABASE_URL preferred over DATABASE_URL)."""
    url = os.getenv("TEST_DATABASE_URL") or DATABASE_URL
    if not url:
        pytest.skip("DATABASE_URL / TEST_DATABASE_URL is not configured")
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect():
            pass
    except Exception as exc:  # pragma: no cover - depends on environment
        pytest.skip(f"database is unreachable: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_conn(db_engine):
    """Read-only connection, everything runs inside a transaction that never commits."""
    conn = db_engine.connect()
    trans = conn.begin()
    yield conn
    trans.rollback()
    conn.close()


@pytest.fixture(scope="session")
def schema_conn(db_engine):
    """Return a connection with a fresh (rolled back) transaction for catalog reads."""
    with db_engine.connect() as conn:
        trans = conn.begin()
        yield conn
        trans.rollback()


@pytest.fixture
def schema(schema_conn):
    return SchemaSnapshot(schema_conn)


class SchemaSnapshot:
    """Lazy accessor over the target database's catalog (first search_path schema)."""

    def __init__(self, conn):
        self.conn = conn
        self.schema = conn.execute(text("SELECT current_schema()")).scalar_one()
        self._columns: dict[str, dict[str, ColumnInfo]] = {}
        self._tables: set[str] | None = None

    @property
    def tables(self) -> set[str]:
        if self._tables is None:
            self._tables = set(
                self.conn.execute(
                    text(
                        """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = :schema AND table_type = 'BASE TABLE'
                        """
                    ),
                    {"schema": self.schema},
                ).scalars()
            )
        return self._tables

    def columns(self, table: str) -> dict[str, "ColumnInfo"]:
        if table not in self._columns:
            rows = self.conn.execute(
                text(
                    """
                    SELECT column_name, data_type, udt_name, character_maximum_length,
                           is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = :schema AND table_name = :table
                    """
                ),
                {"schema": self.schema, "table": table},
            ).mappings()
            self._columns[table] = {row["column_name"]: ColumnInfo(row) for row in rows}
        return self._columns[table]

    def primary_keys(self, table: str) -> list[str]:
        return list(
            self.conn.execute(
                text(
                    """
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY (i.indkey)
                    WHERE i.indrelid = CAST(:qualified AS regclass) AND i.indisprimary
                    ORDER BY array_position(i.indkey, a.attnum)
                    """
                ),
                {"qualified": f"{self.schema}.{table}"},
            ).scalars()
        )

    def unique_constraints(self, table: str) -> set[frozenset[str]]:
        return {
            frozenset(parts)
            for parts in self.conn.execute(
                text(
                    """
                    SELECT array_agg(a.attname ORDER BY k.ord)
                    FROM pg_constraint c
                    CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord)
                    JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
                    WHERE c.conrelid = CAST(:qualified AS regclass) AND c.contype IN ('u', 'p')
                    GROUP BY c.conname
                    """
                ),
                {"qualified": f"{self.schema}.{table}"},
            ).scalars()
        }

    def unique_indexes(self, table: str) -> set[frozenset[str]]:
        return {
            frozenset(parts)
            for parts in self.conn.execute(
                text(
                    """
                    SELECT array_agg(a.attname ORDER BY k.ord)
                    FROM pg_index i
                    CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord)
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.attnum
                    WHERE i.indrelid = CAST(:qualified AS regclass) AND i.indisunique
                    GROUP BY i.indexrelid
                    """
                ),
                {"qualified": f"{self.schema}.{table}"},
            ).scalars()
        }

    def foreign_keys(self, table: str) -> dict[str, "ForeignKeyInfo"]:
        rows = self.conn.execute(
            text(
                """
                SELECT con.conname,
                       att.attname AS column_name,
                       ref_att.attname AS referent_column,
                       ref_ns.nspname AS referent_schema,
                       ref_cls.relname AS referent_table,
                       con.condeferrable,
                       con.confdeltype
                FROM pg_constraint con
                CROSS JOIN LATERAL unnest(con.conkey, con.confkey) AS key(attnum, ref_attnum)
                JOIN pg_attribute att
                  ON att.attrelid = con.conrelid AND att.attnum = key.attnum
                JOIN pg_class ref_cls ON ref_cls.oid = con.confrelid
                JOIN pg_namespace ref_ns ON ref_ns.oid = ref_cls.relnamespace
                JOIN pg_attribute ref_att
                  ON ref_att.attrelid = ref_cls.oid AND ref_att.attnum = key.ref_attnum
                WHERE con.conrelid = CAST(:qualified AS regclass) AND con.contype = 'f'
                ORDER BY con.conname, att.attname
                """
            ),
            {"qualified": f"{self.schema}.{table}"},
        ).mappings()
        return {
            row["column_name"]: ForeignKeyInfo(
                name=row["conname"],
                table=row["referent_table"],
                column=row["referent_column"],
                on_delete=row["confdeltype"],
                deferrable=row["condeferrable"],
            )
            for row in rows
        }

    def enum_labels(self, type_name: str) -> list[str]:
        return list(
            self.conn.execute(
                text(
                    """
                    SELECT e.enumlabel
                    FROM pg_type t
                    JOIN pg_namespace n ON n.oid = t.typnamespace
                    JOIN pg_enum e ON e.enumtypid = t.oid
                    WHERE n.nspname = :schema AND t.typname = :name
                    ORDER BY e.enumsortorder
                    """
                ),
                {"schema": self.schema, "name": type_name},
            ).scalars()
        )

    def has_unique_index(self, table: str, columns: set[str]) -> bool:
        """Unique via constraint or unique (non-partial) index, single- or multi-column."""
        uniques = self.unique_constraints(table) | self.unique_indexes(table)
        target = frozenset(columns)
        return any(target <= u for u in uniques)

    def has_index(self, table: str, columns: set[str]) -> bool:
        """Any index (including PK/unique) leading with exactly these columns."""
        parts_sets = [
            frozenset(parts)
            for parts in self.conn.execute(
                text(
                    """
                    SELECT array_agg(a.attname)
                    FROM pg_index i
                    CROSS JOIN LATERAL unnest(i.indkey) AS k(attnum)
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.attnum
                    WHERE i.indrelid = CAST(:qualified AS regclass)
                    GROUP BY i.indexrelid
                    """
                ),
                {"qualified": f"{self.schema}.{table}"},
            ).scalars()
        ]
        target = frozenset(columns)
        return any(target <= p for p in parts_sets)


class ColumnInfo:
    def __init__(self, row):
        self.name = row["column_name"]
        self.data_type = row["data_type"]  # e.g. "uuid", "bytea", "character varying"
        self.udt_name = row["udt_name"]  # e.g. "uuid", "bytea", "varchar", "_bytea" (array)
        self.max_length = row["character_maximum_length"]
        self.nullable = row["is_nullable"] == "YES"
        self.default = row["column_default"]

    def __repr__(self):
        return f"ColumnInfo({self.name}: {self.udt_name}{self.max_length or ''}, nullable={self.nullable})"


class ForeignKeyInfo:
    def __init__(self, *, name, table, column, on_delete, deferrable):
        self.name = name
        self.table = table
        self.column = column
        # pg_constraint.confdeltype: a=NO ACTION, r=RESTRICT, c=CASCADE, n=SET NULL, d=SET DEFAULT
        self.on_delete = {
            "a": "NO ACTION",
            "r": "RESTRICT",
            "c": "CASCADE",
            "n": "SET NULL",
            "d": "SET DEFAULT",
        }.get(on_delete, on_delete)
        self.deferrable = deferrable
