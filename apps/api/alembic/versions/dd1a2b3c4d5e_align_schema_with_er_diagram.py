"""align schema with er diagram

Revision ID: dd1a2b3c4d5e
Revises: 100471ae24fd
Create Date: 2026-10-24 23:20:34.302748

Reconciles the database created by revision 100471ae24fd (which followed the first
draft of the ORM models) with the ER diagram:

* users: email varchar(320), password -> password_hash, + stego_key_wrapped?,
  + created_at, drop username
* patients: index on owner_id, CHECK for the 12-byte data_nonce
* files: named UNIQUE on storage_key, CHECK for the 32-byte sha256_plain
* activity_logs: bigint identity PK, enum action, nullable user_id/file_id with FKs
  to users/files, timestamptz created_at

Enum labels are the *member names* (DOCUMENT, AES_256_GCM, ...) because the models
build Enum(...) without values_callable, and nothing is stored as the raw label.

Safe to run on a fresh database too: step 1 handles a schema that is empty (revisions
a1d68b0121d6 / c814d01543ea had empty upgrade() bodies).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dd1a2b3c4d5e"
down_revision: Union[str, Sequence[str], None] = "100471ae24fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum labels are the member *values* (lowercase), because the models pass
# values_callable=... so an Enum member round-trips as "document", not "DOCUMENT".
ENUMS = {
    "file_category": ("document", "image", "other"),
    "pdp_class": ("public", "personal", "sensitive"),
    "cipher_algorithm": ("AES-256-GCM",),
    "activity_action": ("upload", "download", "view", "update", "delete", "login", "logout"),
}


def _enum(name: str) -> sa.Enum:
    return sa.Enum(*ENUMS[name], name=name)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table: str) -> set[str]:
    return {ix["name"] for ix in sa.inspect(op.get_bind()).get_indexes(table)}


def _unique_constraints(table: str) -> set[str]:
    return {uc["name"] for uc in sa.inspect(op.get_bind()).get_unique_constraints(table)}


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    # --- 0. empty schema (earlier revisions were no-ops): create everything -------
    if not _tables():
        _create_from_scratch()
        return

    # --- 1. users ---------------------------------------------------------------
    user_columns = _columns("users")
    if "password_hash" not in user_columns:
        op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    if "password" in user_columns:
        op.execute("UPDATE users SET password_hash = password WHERE password_hash IS NULL")
        op.drop_column("users", "password")
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)

    if "stego_key_wrapped" not in user_columns:
        op.add_column("users", sa.Column("stego_key_wrapped", sa.LargeBinary(), nullable=True))
    if "created_at" not in user_columns:
        op.add_column(
            "users",
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.text("now()"), nullable=False),
        )
    op.alter_column("users", "email", existing_type=sa.String(100),
                    type_=sa.String(320), existing_nullable=False)
    if "username_key" in _unique_constraints("users"):
        op.drop_constraint("users_username_key", "users", type_="unique")
    if "username" in _columns("users"):
        op.drop_column("users", "username")

    # --- 2. patients ------------------------------------------------------------
    if "ix_patients_owner_id" not in _indexes("patients"):
        op.create_index("ix_patients_owner_id", "patients", ["owner_id"])
    op.execute(
        "ALTER TABLE patients DROP CONSTRAINT IF EXISTS ck_patients_data_nonce_len"
    )
    op.create_check_constraint(
        "ck_patients_data_nonce_len", "patients", "length(data_nonce) = 12"
    )

    # --- 3. files ---------------------------------------------------------------
    if "uq_files_storage_key" not in _unique_constraints("files"):
        op.create_unique_constraint("uq_files_storage_key", "files", ["storage_key"])
    op.execute("ALTER TABLE files DROP CONSTRAINT IF EXISTS ck_files_sha256_plain_len")
    op.create_check_constraint(
        "ck_files_sha256_plain_len", "files", "length(sha256_plain) = 32"
    )

    # --- 4. activity_logs -------------------------------------------------------
    # id: uuid -> bigint identity first (the table may be rebuilt, dropping extras).
    _uuid_pk_to_bigint()
    if "file_id" not in _columns("activity_logs"):
        op.add_column("activity_logs", sa.Column("file_id", sa.UUID(), nullable=True))

    # A rebuilt / pre-existing uuid table needs an identity attached; one created by
    # _create_from_scratch already has one.
    if op.get_bind().execute(
        sa.text("SELECT is_identity FROM information_schema.columns "
                "WHERE table_name = 'activity_logs' AND column_name = 'id'")
    ).scalar() != "YES":
        op.execute(
            "ALTER TABLE activity_logs ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY"
        )
        seq = op.get_bind().execute(
            sa.text("SELECT pg_get_serial_sequence('activity_logs', 'id')")
        ).scalar_one()
        op.execute(f"SELECT setval('{seq}', COALESCE(max(id), 0) + 1, false) FROM activity_logs")

    op.alter_column("activity_logs", "user_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column(
        "activity_logs", "created_at",
        existing_type=sa.String(255),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using=_is_timestamp("created_at"),
        server_default=sa.text("now()"),
    )

    if "ix_activity_logs_id" in _indexes("activity_logs"):
        op.drop_index("ix_activity_logs_id", table_name="activity_logs")
    if "ix_activity_logs_user_id" not in _indexes("activity_logs"):
        op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"])
    if "ix_activity_logs_file_id" not in _indexes("activity_logs"):
        op.create_index("ix_activity_logs_file_id", "activity_logs", ["file_id"])

    existing_fks = {
        tuple(fk["constrained_columns"])
        for fk in sa.inspect(op.get_bind()).get_foreign_keys("activity_logs")
    }
    if ("user_id",) not in existing_fks:
        op.create_foreign_key(
            "fk_activity_logs_user_id", "activity_logs", "users", ["user_id"], ["id"]
        )
    if ("file_id",) not in existing_fks:
        op.create_foreign_key(
            "fk_activity_logs_file_id", "activity_logs", "files", ["file_id"], ["id"]
        )

    # --- 5. enum types (after activity_logs.action is ready to be cast) ---------
    for name in ENUMS:
        _reconcile_enum(name, ENUMS[name])
    op.alter_column(
        "activity_logs", "action",
        existing_type=sa.String(255),
        type_=_enum("activity_action"),
        existing_nullable=False,
        postgresql_using="lower(action)::activity_action",
    )


STAGING_TABLE = "activity_logs_uuid_staging"


def _is_timestamp(column_sql: str) -> str:
    """SQL expression: parse ISO-8601 text, else fall back to now().

    Inserted values may not be valid timestamps (e.g. from the backup table, whose
    columns are all text).
    """
    return (
        f"CASE WHEN {column_sql} ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}' "
        f"THEN {column_sql}::timestamptz ELSE now() END"
    )


def _uuid_pk_to_bigint() -> None:
    """Change activity_logs.id from uuid to bigint, keeping existing rows.

    A uuid cannot be cast to bigint, so when the table has rows they are staged in a
    temporary table and the table is recreated with a bigint identity PK; rows are
    re-inserted in ascending created_at order (UUIDv4 is random, so creation order is
    the only meaningful ordering) and the new ids follow it.
    """
    bind = op.get_bind()
    has_rows = bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM activity_logs)")).scalar()

    if not has_rows:
        op.execute("ALTER TABLE activity_logs ALTER COLUMN id DROP DEFAULT")
        op.execute("ALTER TABLE activity_logs ALTER COLUMN id TYPE bigint USING 0")
        return

    # Stage, then recreate: uuid -> bigint is not castable, so rows are copied.
    op.execute(f"CREATE TEMP TABLE {STAGING_TABLE} AS TABLE activity_logs")
    op.execute("DROP TABLE activity_logs")
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("created_at", sa.String(255), nullable=False),
    )
    op.execute(
        f"""
        INSERT INTO activity_logs (user_id, action, created_at)
        SELECT user_id, action, created_at FROM {STAGING_TABLE}
        ORDER BY created_at, id
        """
    )
    op.execute(f"DROP TABLE {STAGING_TABLE}")


def downgrade() -> None:
    op.drop_constraint("fk_activity_logs_file_id", "activity_logs", type_="foreignkey")
    op.drop_constraint("fk_activity_logs_user_id", "activity_logs", type_="foreignkey")
    op.drop_index("ix_activity_logs_file_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_user_id", table_name="activity_logs")
    op.alter_column("activity_logs", "created_at",
                    existing_type=sa.DateTime(timezone=True),
                    type_=sa.String(255),
                    existing_nullable=False,
                    postgresql_using="created_at::text")
    op.alter_column("activity_logs", "action",
                    existing_type=_enum("activity_action"),
                    type_=sa.String(255),
                    existing_nullable=False,
                    postgresql_using="action::text")
    op.alter_column("activity_logs", "user_id", existing_type=sa.UUID(), nullable=False)
    op.execute("ALTER TABLE activity_logs ALTER COLUMN id DROP IDENTITY IF EXISTS")
    op.execute(f"DROP TABLE IF EXISTS {STAGING_TABLE}")
    op.execute(f"CREATE TEMP TABLE {STAGING_TABLE} AS TABLE activity_logs")
    op.execute("DELETE FROM activity_logs")
    op.execute("ALTER TABLE activity_logs ALTER COLUMN id TYPE uuid USING gen_random_uuid()")
    op.execute(
        f"""
        INSERT INTO activity_logs (id, user_id, action, created_at)
        SELECT gen_random_uuid(), user_id, action,
               to_char(created_at::timestamptz, 'YYYY-MM-DD"T"HH24:MI:SSOF')
        FROM {STAGING_TABLE} ORDER BY id
        """
    )
    op.execute(f"DROP TABLE {STAGING_TABLE}")
    op.create_index("ix_activity_logs_id", "activity_logs", ["id"])
    op.drop_column("activity_logs", "file_id")

    op.drop_constraint("ck_files_sha256_plain_len", "files", type_="check")
    op.drop_constraint("uq_files_storage_key", "files", type_="unique")
    op.drop_constraint("ck_patients_data_nonce_len", "patients", type_="check")
    op.drop_index("ix_patients_owner_id", table_name="patients")

    # username was dropped going forward and has no faithful source; derive it from
    # the email local-part so the NOT NULL column can be re-added on populated tables.
    op.add_column("users", sa.Column("username", sa.String(50), nullable=True))
    op.execute("UPDATE users SET username = left(split_part(email, '@', 1), 50)")
    op.alter_column("users", "username", existing_type=sa.String(50), nullable=False)
    op.create_unique_constraint("users_username_key", "users", ["username"])
    # password_hash is the real (hashed) secret, so it is the only honest backfill.
    op.add_column("users", sa.Column("password", sa.String(255), nullable=True))
    op.execute("UPDATE users SET password = password_hash")
    op.alter_column("users", "password", existing_type=sa.String(255), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(320),
                    type_=sa.String(100), existing_nullable=False)
    op.drop_column("users", "created_at")
    op.drop_column("users", "stego_key_wrapped")
    op.drop_column("users", "password_hash")

    # file_category / pdp_class / cipher_algorithm existed before this revision; only
    # the type introduced here goes away on downgrade.
    op.execute("DROP TYPE IF EXISTS activity_action")


def _create_enums() -> None:
    """CREATE TYPE ... , tolerating types already present."""
    for name in ENUMS:
        op.execute(f'DO $$ BEGIN CREATE TYPE {name} AS ENUM ('
                   f"{', '.join(repr(v) for v in ENUMS[name])}); "
                   f"EXCEPTION WHEN duplicate_object THEN NULL; END $$;")


def _replace_enum(name: str, labels: tuple[str, ...]) -> None:
    """Swap in a fresh type (old one already dropped / never used)."""
    op.execute(f"DROP TYPE IF EXISTS {name}")
    op.execute(f"CREATE TYPE {name} AS ENUM ({', '.join(repr(v) for v in labels)})")


def _reconcile_enum(name: str, labels: tuple[str, ...]) -> None:
    """Make the type have exactly `labels`, converting existing column data if needed."""
    t = op.get_bind().execute(sa.text("SELECT to_regtype(:n)"), {"n": name}).scalar()
    if t is None:
        _replace_enum(name, labels)
        return

    existing = list(
        op.get_bind().execute(
            sa.text(
                "SELECT e.enumlabel FROM pg_enum e "
                "JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = :n ORDER BY e.enumsortorder"
            ),
            {"n": name},
        ).scalars()
    )
    if existing == list(labels):
        return

    # The labels differ (e.g. DOCUMENT vs document). Enum values cannot be renamed
    # in place reliably, so: retype columns to text, then cast text to the new type.
    columns = op.get_bind().execute(
        sa.text(
            """
            SELECT c.table_name, c.column_name
            FROM information_schema.columns c
            WHERE c.udt_name = :n AND c.table_schema = current_schema()
            """
        ),
        {"n": name},
    ).all()

    for table, column in columns:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE text")
    op.execute(f"ALTER TYPE {name} RENAME TO {name}_old")
    op.execute(f"CREATE TYPE {name} AS ENUM ({', '.join(repr(v) for v in labels)})")
    for table, column in columns:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {name} "
            f"USING lower({column})::text::{name}"
        )
    op.execute(f"DROP TYPE {name}_old")


def _create_from_scratch() -> None:
    """Full schema for a database where the earlier migrations were empty no-ops."""
    _create_enums()

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("stego_key_wrapped", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_id", "users", ["id"])

    op.create_table(
        "patients",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("owner_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("data_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("data_nonce", sa.LargeBinary(12), nullable=False),
        sa.Column("dek_wrapped", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(data_nonce) = 12", name="ck_patients_data_nonce_len"),
    )
    op.create_index("ix_patients_id", "patients", ["id"])
    op.create_index("ix_patients_owner_id", "patients", ["owner_id"])

    op.create_table(
        "files",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("owner_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("patient_id", sa.UUID(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("category", _enum("file_category"), nullable=False),
        sa.Column("pdp_class", _enum("pdp_class"), nullable=False),
        sa.Column("mime_type", sa.String(127), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("original_name_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("sha256_plain", sa.LargeBinary(32), nullable=False),
        sa.Column("algorithm", _enum("cipher_algorithm"), nullable=False),
        sa.Column("format_version", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("iv", sa.LargeBinary(), nullable=True),
        sa.Column("auth_tag", sa.LargeBinary(), nullable=True),
        sa.Column("dek_wrapped", sa.LargeBinary(), nullable=False),
        sa.Column("mac_key_wrapped", sa.LargeBinary(), nullable=True),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(sha256_plain) = 32", name="ck_files_sha256_plain_len"),
        sa.UniqueConstraint("storage_key", name="uq_files_storage_key"),
    )
    op.create_index("ix_files_owner_id", "files", ["owner_id"])
    op.create_index("ix_files_patient_id", "files", ["patient_id"])

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", _enum("activity_action"), nullable=False),
        sa.Column("file_id", sa.UUID(), sa.ForeignKey("files.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"])
    op.create_index("ix_activity_logs_file_id", "activity_logs", ["file_id"])
