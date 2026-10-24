"""Expected database schema for SiArsip, transcribed from the ER diagram.

Legend used by the diagram:
    PK  primary key          FK  foreign key
    UQ  unique               KEY ciphertext / wrapped key
    name?  nullable column

Relationships:
    users.id      1 ──< patients.owner_id   (exactly one, NOT NULL)  "owns"
    users.id      1 ──< files.owner_id      (exactly one, NOT NULL)  "owns" (denormalised)
    patients.id   1 ──< files.patient_id    (exactly one, NOT NULL)  "has"
    users.id      0 ──< activity_logs.user_id?  (nullable)           "acts"
    files.id      0 ──< activity_logs.file_id?  (nullable)           "logged_in"
"""

from dataclasses import dataclass, field

UUID = "uuid"
BYTEA = "bytea"
VARCHAR = "character varying"
BIGINT = "bigint"
SMALLINT = "smallint"
TIMESTAMPTZ = "timestamp with time zone"


@dataclass(frozen=True)
class Column:
    type: str
    length: int | None = None
    nullable: bool = False
    # For enum columns: expected labels in order.
    enum: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Table:
    name: str
    primary_key: str
    columns: dict[str, Column]
    # Single-column uniques are declared on the column spec (UQ flag in the diagram).
    unique: set[str] = field(default_factory=set)
    # Composite uniques, rendered with a horizontal UQ bar under both columns.
    composite_unique: set[frozenset[str]] = field(default_factory=set)
    # Foreign key column -> referenced table. All FKs point at the referenced table's PK.
    foreign_keys: dict[str, str] = field(default_factory=dict)


USERS = Table(
    name="users",
    primary_key="id",
    columns={
        "id": Column(UUID),
        "email": Column(VARCHAR, 320),
        "password_hash": Column(VARCHAR, 255),
        "stego_key_wrapped?": Column(BYTEA, nullable=True),
        "created_at": Column(TIMESTAMPTZ),
    },
    unique={"email"},
)

PATIENTS = Table(
    name="patients",
    primary_key="id",
    columns={
        "id": Column(UUID),
        "owner_id": Column(UUID),
        "data_encrypted": Column(BYTEA),
        "data_nonce": Column(BYTEA, 12),
        "dek_wrapped": Column(BYTEA),
        "created_at": Column(TIMESTAMPTZ),
        "updated_at": Column(TIMESTAMPTZ),
    },
    foreign_keys={"owner_id": "users"},
)

FILES = Table(
    name="files",
    primary_key="id",
    columns={
        "id": Column(UUID),
        "owner_id": Column(UUID),
        "patient_id": Column(UUID),
        "category": Column(
            "file_category",
            enum=("identity_scan", "office_document", "video", "clinical_image"),
        ),
        "pdp_class": Column("pdp_class", enum=("specific", "general")),
        "mime_type": Column(VARCHAR, 127),
        "size_bytes": Column(BIGINT),
        "original_name_encrypted": Column(BYTEA),
        "sha256_plain": Column(BYTEA, 32),
        "algorithm": Column("cipher_algorithm", enum=("aes-gcm", "des-cbc", "rc4")),
        "format_version": Column(SMALLINT),
        "iv?": Column(BYTEA, nullable=True),
        "auth_tag": Column(BYTEA),
        "dek_wrapped": Column(BYTEA),
        "mac_key_wrapped?": Column(BYTEA, nullable=True),
        "storage_key": Column(VARCHAR, 255),
        "created_at": Column(TIMESTAMPTZ),
    },
    unique={"storage_key"},
    foreign_keys={"owner_id": "users", "patient_id": "patients"},
)

ACTIVITY_LOGS = Table(
    name="activity_logs",
    primary_key="id",
    columns={
        "id": Column(BIGINT),
        "user_id?": Column(UUID, nullable=True),
        "action": Column(
            "activity_action",
            enum=("upload", "download", "view", "update", "delete", "login", "logout"),
        ),
        "file_id?": Column(UUID, nullable=True),
        "created_at": Column(TIMESTAMPTZ),
    },
    foreign_keys={"user_id": "users", "file_id": "files"},
)

TABLES: dict[str, Table] = {
    t.name: t for t in (USERS, PATIENTS, FILES, ACTIVITY_LOGS)
}


def real_columns(table: Table) -> dict[str, Column]:
    """{column_name: Column} with the diagram's trailing '?' stripped."""
    return {name.rstrip("?"): col for name, col in table.columns.items()}


def nullable_columns(table: Table) -> set[str]:
    return {name.rstrip("?") for name, col in table.columns.items() if col.nullable}


def non_nullable_columns(table: Table) -> set[str]:
    return {name.rstrip("?") for name, col in table.columns.items() if not col.nullable}
