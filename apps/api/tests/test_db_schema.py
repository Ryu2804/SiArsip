"""Structural checks of the SiArsip database against the ER diagram.

Every test is parametrised over ``db_schema.TABLES`` so a single failing column or
constraint shows up as its own test id, e.g. ``TestColumns::test_column_spec[files.auth_tag]``.

Nothing is written to the database: all catalog reads happen inside a transaction that
is rolled back in ``conftest.py``.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.db_schema import (
    ACTIVITY_LOGS,
    FILES,
    PATIENTS,
    TABLES,
    USERS,
    nullable_columns,
    non_nullable_columns,
    real_columns,
)

TABLES_PARAMS = pytest.mark.parametrize("table_name", sorted(TABLES), ids=sorted(TABLES))

# Referential actions that keep children pointing at a valid parent are acceptable;
# the diagram only states cardinality, not ON DELETE semantics.
DELETE_ACTIONS = {"NO ACTION", "RESTRICT", "CASCADE"}


class TestTablesExist:
    @TABLES_PARAMS
    def test_table_exists(self, schema, table_name):
        assert table_name in schema.tables, (
            f"table '{table_name}' missing; found: {sorted(schema.tables)}"
        )

    def test_no_unexpected_tables(self, schema):
        expected = set(TABLES) | {"alembic_version"}
        unexpected = schema.tables - expected
        assert not unexpected, f"unexpected tables in schema: {sorted(unexpected)}"


class TestColumns:
    @TABLES_PARAMS
    def test_no_missing_or_extra_columns(self, schema, table_name):
        expected = set(real_columns(TABLES[table_name]))
        actual = set(schema.columns(table_name))
        missing = expected - actual
        extra = actual - expected
        assert not missing and not extra, f"missing={sorted(missing)} extra={sorted(extra)}"

    @pytest.mark.parametrize(
        ("table_name", "column_name"),
        [
            (t, c)
            for t in sorted(TABLES)
            for c in sorted(real_columns(TABLES[t]))
        ],
        ids=[f"{t}.{c}" for t in sorted(TABLES) for c in sorted(real_columns(TABLES[t]))],
    )
    def test_column_spec(self, schema, table_name, column_name):
        expected = real_columns(TABLES[table_name]).get(column_name)
        if expected is None:
            pytest.skip(f"column {table_name}.{column_name} does not exist")

        actual = schema.columns(table_name)[column_name]

        assert actual.nullable == expected.nullable, (
            f"{table_name}.{column_name}: nullable={actual.nullable}, "
            f"expected {expected.nullable} (diagram marks nullable with '?')"
        )

        if expected.enum is not None:
            assert actual.data_type == "USER-DEFINED" or actual.udt_name == expected.type, (
                f"{table_name}.{column_name}: type {actual.udt_name!r}, "
                f"expected enum {expected.type!r}"
            )
            return

        assert actual.data_type == expected.type, (
            f"{table_name}.{column_name}: type {actual.data_type!r}, expected {expected.type!r}"
        )
        if expected.length is None:
            return
        if expected.type != "bytea":
            assert actual.max_length == expected.length, (
                f"{table_name}.{column_name}: length {actual.max_length}, "
                f"expected {expected.length}"
            )
            return
        # Postgres silently ignores bytea(N): the only way to pin a bytea length is a
        # CHECK constraint. Enforce it here so nonces/hashes cannot be stored at any size.
        assert self._has_length_check(schema, table_name, column_name, expected.length), (
            f"{table_name}.{column_name}: must be exactly {expected.length} bytes; "
            f"add CHECK (length({column_name}) = {expected.length})"
        )

    @staticmethod
    def _has_length_check(schema, table_name, column_name, n):
        sql = """
            SELECT pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            WHERE c.conrelid = CAST(:qualified AS regclass) AND c.contype = 'c'
        """
        for definition in schema.conn.execute(
            text(sql), {"qualified": f"{schema.schema}.{table_name}"}
        ).scalars():
            compact = definition.replace(" ", "").replace('"', "").lower()
            if f"length({column_name})={n}" in compact or f"octet_length({column_name})={n}" in compact:
                return True
        return False


class TestEnums:
    @pytest.mark.parametrize(
        ("table_name", "column_name", "labels"),
        [
            ("files", "category", ("identity_scan", "office_document", "video", "clinical_image")),
            ("files", "pdp_class", ("specific", "general")),
            ("files", "algorithm", ("aes-gcm", "des-cbc", "rc4")),
            (
                "activity_logs",
                "action",
                ("upload", "download", "view", "update", "delete", "login", "logout"),
            ),
        ],
        ids=["file_category", "pdp_class", "cipher_algorithm", "activity_action"],
    )
    def test_enum_labels(self, schema, table_name, column_name, labels):
        column = schema.columns(table_name).get(column_name)
        if column is None:
            pytest.skip(f"column {table_name}.{column_name} does not exist")

        actual = schema.enum_labels(column.udt_name)
        assert set(labels) <= set(actual), (
            f"enum {column.udt_name}: missing labels "
            f"{sorted(set(labels) - set(actual))} (has {sorted(actual)})"
        )


class TestPrimaryKeys:
    @TABLES_PARAMS
    def test_primary_key(self, schema, table_name):
        expected = TABLES[table_name].primary_key
        actual = schema.primary_keys(table_name)
        assert actual == [expected], (
            f"{table_name}: primary key {actual}, expected ['{expected}']"
        )

    def test_activity_logs_id_is_not_a_uuid(self, schema):
        """activity_logs.id is a bigint in the diagram, unlike every other PK."""
        column = schema.columns("activity_logs").get("id")
        if column is None:
            pytest.skip("activity_logs.id does not exist")
        assert column.data_type == "bigint", f"activity_logs.id is {column.data_type!r}"


class TestUniques:
    @TABLES_PARAMS
    def test_single_column_uniques(self, schema, table_name):
        for column in sorted(TABLES[table_name].unique):
            assert schema.has_unique_index(table_name, {column}), (
                f"{table_name}.{column} must be UQ (diagram)"
            )

    def test_files_storage_key_is_unique(self, schema):
        assert schema.has_unique_index("files", {"storage_key"})


class TestForeignKeys:
    @pytest.mark.parametrize(
        ("table_name", "column_name", "target_table"),
        [
            (t, column, target)
            for t in sorted(TABLES)
            for column, target in sorted(TABLES[t].foreign_keys.items())
        ],
        ids=[
            f"{t}.{c}->{target}"
            for t in sorted(TABLES)
            for c, target in sorted(TABLES[t].foreign_keys.items())
        ],
    )
    def test_foreign_key(self, schema, table_name, column_name, target_table):
        fk = schema.foreign_keys(table_name).get(column_name)
        assert fk is not None, (
            f"{table_name}.{column_name} missing FK to {target_table}"
        )
        assert fk.table == target_table, (
            f"{table_name}.{column_name} references {fk.table}, expected {target_table}"
        )
        assert fk.column == TABLES[target_table].primary_key, (
            f"{table_name}.{column_name} -> {fk.table}.{fk.column}, "
            f"expected {fk.table}.{TABLES[target_table].primary_key}"
        )
        assert fk.on_delete in DELETE_ACTIONS, (
            f"{table_name}.{column_name}: ON DELETE {fk.on_delete} would orphan rows"
        )

    @TABLES_PARAMS
    def test_no_extra_foreign_keys(self, schema, table_name):
        expected = set(TABLES[table_name].foreign_keys)
        actual = set(schema.foreign_keys(table_name))
        assert actual == expected, (
            f"{table_name}: FK columns {sorted(actual)}, expected {sorted(expected)}"
        )

    @TABLES_PARAMS
    def test_fk_columns_are_indexed(self, schema, table_name):
        """Postgres does not index FK columns automatically; lookups need them indexed."""
        for column in sorted(TABLES[table_name].foreign_keys):
            assert schema.has_index(table_name, {column}), (
                f"{table_name}.{column} has an FK but no index (slow deletes/joins)"
            )

    def test_files_owner_and_patient_are_independent_fks(self, schema):
        """files must reference both users.id and patients.id, not one via the other."""
        fks = schema.foreign_keys("files")
        assert {c: f.table for c, f in fks.items()} == {
            "owner_id": "users",
            "patient_id": "patients",
        }


def insert_user(conn, email="a@example.com"):
    return conn.execute(
        text(
            """
            INSERT INTO users (id, email, password_hash, created_at)
            VALUES (gen_random_uuid(), :email, 'x', now())
            RETURNING id
            """
        ),
        {"email": email},
    ).scalar_one()


def insert_patient(conn, owner_id):
    return conn.execute(
        text(
            """
            INSERT INTO patients (id, owner_id, data_encrypted, data_nonce, dek_wrapped,
                                  created_at, updated_at)
            VALUES (gen_random_uuid(), :owner_id, :data, :nonce, :dek, now(), now())
            RETURNING id
            """
        ),
        {"owner_id": owner_id, "data": b"ct", "nonce": b"0" * 12, "dek": b"dek"},
    ).scalar_one()


def insert_file(conn, **overrides):
    user_id = insert_user(conn, email=overrides.pop("email", "f@example.com"))
    patient_id = insert_patient(conn, user_id)
    params = {
        "owner": user_id,
        "patient": patient_id,
        "category": "identity_scan",
        "pdp": "specific",
        "size": 10,
        "alg": "aes-gcm",
        "iv": b"i" * 12,
        "tag": b"t" * 16,
        "mac": None,
        "storage_key": "k/x",
    }
    params.update(overrides)
    conn.execute(
        text(
            """
            INSERT INTO files (id, owner_id, patient_id, category, pdp_class, mime_type,
                               size_bytes, original_name_encrypted, sha256_plain,
                               algorithm, format_version, iv, auth_tag, dek_wrapped,
                               mac_key_wrapped, storage_key, created_at)
            VALUES (gen_random_uuid(), :owner, :patient, :category, :pdp,
                    'application/pdf', :size, 'n', :sha, :alg, 1, :iv, :tag,
                    'dek', :mac, :storage_key, now())
            """
        ),
        {**params, "sha": b"0" * 32},
    )
    return user_id, patient_id


class TestConstraintsRejectBadData:
    """Behavioural checks against a live DB, rolled back afterwards."""

    @pytest.fixture
    def workspace(self, db_conn):
        tx = db_conn.begin_nested()
        yield db_conn
        tx.rollback()

    def _insert_user(self, conn, email="a@example.com"):
        return conn.execute(
            text(
                """
                INSERT INTO users (id, email, password_hash, created_at)
                VALUES (gen_random_uuid(), :email, 'x', now())
                RETURNING id
                """
            ),
            {"email": email},
        ).scalar_one()

    def _insert_patient(self, conn, owner_id):
        return conn.execute(
            text(
                """
                INSERT INTO patients (id, owner_id, data_encrypted, data_nonce, dek_wrapped,
                                      created_at, updated_at)
                VALUES (gen_random_uuid(), :owner_id, :data, :nonce, :dek, now(), now())
                RETURNING id
                """
            ),
            {"owner_id": owner_id, "data": b"ct", "nonce": b"0" * 12, "dek": b"dek"},
        ).scalar_one()

    def test_users_email_unique(self, workspace):
        self._insert_user(workspace)
        with pytest.raises(IntegrityError):
            self._insert_user(workspace)  # same email, different row

    def test_patients_owner_must_exist(self, workspace):
        with pytest.raises(IntegrityError):
            self._insert_patient(workspace, "00000000-0000-0000-0000-000000000000")

    def test_patients_owner_id_required(self, workspace):
        with pytest.raises(IntegrityError):
            workspace.execute(
                text(
                    """
                    INSERT INTO patients (id, data_encrypted, data_nonce, dek_wrapped,
                                          created_at, updated_at)
                    VALUES (gen_random_uuid(), :data, :nonce, :dek, now(), now())
                    """
                ),
                {"data": b"ct", "nonce": b"0" * 12, "dek": b"dek"},
            )

    def test_files_storage_key_unique(self, workspace):
        user_id = self._insert_user(workspace)
        patient_id = self._insert_patient(workspace, user_id)
        params = {"owner": user_id, "patient": patient_id}
        sql = text(
            """
            INSERT INTO files (id, owner_id, patient_id, category, pdp_class, mime_type,
                               size_bytes, original_name_encrypted, sha256_plain, algorithm,
                               format_version, iv, auth_tag, dek_wrapped, storage_key,
                               created_at)
            VALUES (gen_random_uuid(), :owner, :patient, 'identity_scan', 'specific',
                    'application/pdf', 10, :name, :sha, 'aes-gcm', 1, :iv, :tag, :dek,
                    :storage_key, now())
            """
        )
        base = {"name": b"n", "sha": b"0" * 32, "dek": b"dek", "iv": b"i" * 12,
                "tag": b"t" * 16, **params}
        workspace.execute(sql, {**base, "storage_key": "bucket/aaa"})
        with pytest.raises(IntegrityError):
            workspace.execute(sql, {**base, "storage_key": "bucket/aaa"})

    def test_activity_logs_ids_are_nullable(self, workspace):
        """user_id? and file_id? are optional: a system event has neither."""
        workspace.execute(
            text(
                """
                INSERT INTO activity_logs (action, created_at)
                VALUES ('login', now())
                """
            )
        )

    def test_nonce_must_be_twelve_bytes(self, workspace):
        user_id = self._insert_user(workspace)
        with pytest.raises(DBAPIError):
            workspace.execute(
                text(
                    """
                    INSERT INTO patients (id, owner_id, data_encrypted, data_nonce,
                                          dek_wrapped, created_at, updated_at)
                    VALUES (gen_random_uuid(), :owner_id, :data, :nonce, :dek, now(), now())
                    """
                ),
                {"owner_id": user_id, "data": b"ct", "nonce": b"short", "dek": b"dek"},
            )


class TestFileIntegrityConstraints:
    """Columns that look optional but are not: an untagged row cannot be verified."""

    @pytest.mark.parametrize(
        ("label", "overrides"),
        [
            ("auth_tag_null", {"tag": None}),
            ("size_zero", {"size": 0}),
            ("size_over_100mb", {"size": 100 * 1024 * 1024 + 1}),
            ("aes_without_iv", {"iv": None}),
            ("aes_with_mac_key", {"mac": b"m"}),
            ("old_enum_label", {"category": "document"}),
        ],
    )
    def test_bad_rows_rejected(self, db_conn, label, overrides):
        nested = db_conn.begin_nested()
        try:
            insert_file(db_conn, **overrides)
        except (IntegrityError, DBAPIError):
            nested.rollback()
            return
        nested.rollback()
        pytest.fail(f"{label}: row was accepted but must violate a constraint")

    def test_valid_row_accepted(self, db_conn):
        nested = db_conn.begin_nested()
        insert_file(db_conn)
        nested.rollback()

    def test_storage_key_has_one_unique(self, schema):
        uniques = {
            u for u in (schema.unique_constraints("files") | schema.unique_indexes("files"))
            if u == frozenset({"storage_key"})
        }
        assert len(uniques) == 1, f"duplicate UNIQUE on storage_key: {uniques}"

    def test_deleting_patient_cascades_to_files(self, db_conn):
        nested = db_conn.begin_nested()
        _, patient_id = insert_file(db_conn)
        db_conn.execute(text("DELETE FROM patients WHERE id = :i"), {"i": patient_id})
        remaining = db_conn.execute(
            text("SELECT count(*) FROM files WHERE patient_id = :i"), {"i": patient_id}
        ).scalar_one()
        nested.rollback()
        assert remaining == 0
