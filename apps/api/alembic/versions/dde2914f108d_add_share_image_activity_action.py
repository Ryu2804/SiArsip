"""add share_image activity action

Revision ID: dde2914f108d
Revises: 82ef1308e7df
Create Date: 2026-10-25 19:40:40.952301

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dde2914f108d'
down_revision: Union[str, Sequence[str], None] = '82ef1308e7df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass


def _add_enum_value(type_name: str, label: str) -> None:
    """ALTER TYPE ... ADD VALUE on a dedicated autocommit connection."""
    from sqlalchemy import create_engine, text


    url = op.get_bind().engine.url
    engine = create_engine(url, isolation_level="AUTOCOMMIT", poolclass=None)
    try:
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '{label}'"))
    finally:
        engine.dispose()
