"""add share_image activity action

Revision ID: dde2914f108d
Revises: 82ef1308e7df
Create Date: 2026-10-25 19:40:40.952301

Originally its upgrade() was a no-op and its helper used a second connection; both are
fixed here (see e5f6a7b8c9d0, which re-applies the label for databases that already
ran the no-op version).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'dde2914f108d'
down_revision: Union[str, Sequence[str], None] = '82ef1308e7df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    _add_enum_value("activity_action", "share_image")

def downgrade() -> None:
    """Downgrade schema: no-op, PostgreSQL cannot remove a single enum value."""
    pass


def _add_enum_value(type_name: str, label: str) -> None:
    """ALTER TYPE ... ADD VALUE on the migration's own connection.

    Not a second connection: DDL created earlier in the migration transaction is
    invisible to other connections until it commits, so a separate connection fails
    with "type ... does not exist".
    """
    from sqlalchemy import text

    op.get_bind().execute(
        text(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '{label}'")
    )
