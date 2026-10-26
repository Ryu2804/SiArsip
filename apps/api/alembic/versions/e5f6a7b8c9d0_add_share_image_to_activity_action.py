"""add share_image to activity_action

Revision ID: e5f6a7b8c9d0
Revises: dde2914f108d
Create Date: 2026-10-26 12:40:00.000000

dde2914f108d was meant to append 'share_image' to the activity_action enum but its
upgrade() was a no-op, so any database built from migrations rejected
ActivityAction.SHARE_IMAGE with "invalid input value for enum activity_action".

Its helper changed the type from a *second* connection. DDL created earlier in the
same migration transaction is not visible to another connection before that
transaction commits, so that helper fails with "type activity_action does not
exist" as soon as an earlier revision actually created the type. This revision runs
the ALTER TYPE on the migration's own connection, where the type always exists.

PostgreSQL cannot drop a single enum value, so there is no downgrade.
"""
from typing import Sequence, Union

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'dde2914f108d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # ADD VALUE IF NOT EXISTS is idempotent, so a database that already has the
    # label (e.g. patched by hand) is left unchanged.
    op.get_bind().execute(text("ALTER TYPE activity_action ADD VALUE IF NOT EXISTS 'share_image'"))

def downgrade() -> None:
    """Downgrade schema: no-op, PostgreSQL cannot remove a single enum value."""
    pass
