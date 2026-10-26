"""activity_logs.file_id -> files.id ON DELETE SET NULL

Revision ID: b7c2d1e4a9f0
Revises: e5f6a7b8c9d0
Create Date: 2026-10-26

Deleting a patient cascades to its files. Until now activity_logs.file_id was a
plain FK, so any file with an audit entry blocked the patient delete with
``ForeignKeyViolation: fk_activity_logs_file_id``. The log entry is kept and only
its file reference is cleared.

Alembic cannot ALTER a constraint's ondelete, so it is dropped and recreated.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b7c2d1e4a9f0"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT = "fk_activity_logs_file_id"


def _file_id_fk() -> dict:
    """The current FOREIGN KEY constraint on activity_logs.file_id ({} if none)."""
    for fk in sa.inspect(op.get_bind()).get_foreign_keys("activity_logs"):
        if fk["constrained_columns"] == ["file_id"]:
            return fk
    return {}


def _replace_fk(ondelete: str | None) -> None:
    current = _file_id_fk()
    if not current:
        return
    op.drop_constraint(current.get("name") or CONSTRAINT, "activity_logs", type_="foreignkey")
    op.create_foreign_key(
        CONSTRAINT,
        "activity_logs",
        "files",
        ["file_id"],
        ["id"],
        ondelete=ondelete,
    )


def upgrade() -> None:
    _replace_fk("SET NULL")


def downgrade() -> None:
    # Existing rows must not dangle before the restrictive FK goes back on.
    op.execute(
        "UPDATE activity_logs SET file_id = NULL WHERE file_id IS NOT NULL "
        "AND file_id NOT IN (SELECT id FROM files)"
    )
    _replace_fk(None)
