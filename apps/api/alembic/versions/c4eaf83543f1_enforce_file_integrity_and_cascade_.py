"""enforce file integrity and cascade deletes

Revision ID: c4eaf83543f1
Revises: 7e9a62f539df
Create Date: 2026-10-24 23:47:17.660540

Brings the database in line with ``app/models/``:

* files.auth_tag is NOT NULL (an untagged row means tampering cannot be detected)
* files.owner_id / files.patient_id cascade from users / patients
* files CHECKs: size range (<= 100 MB), IV presence per algorithm, mac_key per algorithm
* enum labels switched to the model's values (file_category, pdp_class,
  cipher_algorithm)
* the duplicate UNIQUE on storage_key is removed (unique=True already makes one)

Autogenerate does not emit CHECK constraints or enum-label changes for Postgres,
and it renders the new foreign keys without names (so downgrade could not drop
them); those parts were written by hand.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c4eaf83543f1"
down_revision: Union[str, Sequence[str], None] = "7e9a62f539df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Labels exactly as declared in app/models/files.py.
ENUM_LABELS = {
    "file_category": ("identity_scan", "office_document", "video", "clinical_image"),
    "pdp_class": ("specific", "general"),
    "cipher_algorithm": ("aes-gcm", "des-cbc", "rc4"),
}

# Labels were the previous (diagram-era) values; kept for a real downgrade.
OLD_ENUM_LABELS = {
    "file_category": ("document", "image", "other"),
    "pdp_class": ("public", "personal", "sensitive"),
    "cipher_algorithm": ("AES-256-GCM",),
}

FK_OWNER = "fk_files_owner_id"
FK_PATIENT = "fk_files_patient_id"


def upgrade() -> None:
    # 1. Rebuild the enum types with the model's labels. The old labels have no
    #    meaningful mapping onto the new ones, so this requires empty columns and
    #    is verified below rather than silently truncating data.
    _assert_columns_empty("files", "category", "pdp_class", "algorithm")
    for name, labels in ENUM_LABELS.items():
        _replace_enum(name, labels)

    # 2. auth_tag is now mandatory: without it a modified file is indistinguishable
    #    from an authentic one.
    op.alter_column(
        "files",
        "auth_tag",
        existing_type=postgresql.BYTEA(),
        nullable=False,
    )

    # 3. Replace the foreign keys so deletes cascade from users/patients down to files.
    op.drop_constraint("files_owner_id_fkey", "files", type_="foreignkey")
    op.drop_constraint("files_patient_id_fkey", "files", type_="foreignkey")
    op.create_foreign_key(FK_OWNER, "files", "users", ["owner_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key(
        FK_PATIENT, "files", "patients", ["patient_id"], ["id"], ondelete="CASCADE"
    )

    # 4. Integrity CHECKs declared in models/files.py.
    op.create_check_constraint(
        "ck_files_size_range",
        "files",
        "size_bytes > 0 AND size_bytes <= 104857600",
    )
    op.create_check_constraint(
        "ck_files_iv_matches_algorithm",
        "files",
        "(algorithm = 'rc4') = (iv IS NULL)",
    )
    op.create_check_constraint(
        "ck_files_mac_key_matches_algorithm",
        "files",
        "(algorithm = 'aes-gcm') = (mac_key_wrapped IS NULL)",
    )

    # 5. unique=True already builds a UNIQUE; the extra named one only doubles the
    #    write cost per insert.
    op.drop_constraint("uq_files_storage_key", "files", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("uq_files_storage_key", "files", ["storage_key"])

    op.drop_constraint("ck_files_mac_key_matches_algorithm", "files", type_="check")
    op.drop_constraint("ck_files_iv_matches_algorithm", "files", type_="check")
    op.drop_constraint("ck_files_size_range", "files", type_="check")

    op.drop_constraint(FK_OWNER, "files", type_="foreignkey")
    op.drop_constraint(FK_PATIENT, "files", type_="foreignkey")
    op.create_foreign_key("files_owner_id_fkey", "files", "users", ["owner_id"], ["id"])
    op.create_foreign_key(
        "files_patient_id_fkey", "files", "patients", ["patient_id"], ["id"]
    )

    op.alter_column(
        "files",
        "auth_tag",
        existing_type=postgresql.BYTEA(),
        nullable=True,
    )

    _assert_columns_empty("files", "category", "pdp_class", "algorithm")
    for name, labels in OLD_ENUM_LABELS.items():
        _replace_enum(name, labels)


def _assert_columns_empty(table: str, *columns: str) -> None:
    """Refuse to relabel an enum that already holds values we would have to discard."""
    bind = op.get_bind()
    for column in columns:
        distinct = bind.execute(
            sa.text(f"SELECT count(DISTINCT {column}) FROM {table}")
        ).scalar_one()
        if distinct:
            raise RuntimeError(
                f"{table}.{column} holds {distinct} value(s); relabelling the enum "
                "requires migrating those rows explicitly"
            )


def _replace_enum(name: str, labels: tuple[str, ...]) -> None:
    """Swap the type for a fresh one with `labels`.

    DROP TYPE ... CASCADE would drop the columns using it, so the old type is renamed
    aside and every column is retyped to text and then to the new type (the columns are
    empty, verified by _assert_columns_empty).
    """
    bind = op.get_bind()
    columns = bind.execute(
        sa.text(
            """
            SELECT c.table_name, c.column_name
            FROM information_schema.columns c
            WHERE c.udt_name = :name AND c.table_schema = current_schema()
            """
        ),
        {"name": name},
    ).all()

    values = ", ".join(f"'{label}'" for label in labels)
    old = f"{name}_old"
    op.execute(f"DROP TYPE IF EXISTS {old}")
    op.execute(f"ALTER TYPE {name} RENAME TO {old}")
    op.execute(f"CREATE TYPE {name} AS ENUM ({values})")

    for table, column in columns:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE text")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {name} USING {column}::{name}")

    op.execute(f"DROP TYPE {old}")
