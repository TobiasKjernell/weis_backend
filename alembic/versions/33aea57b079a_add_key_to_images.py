"""add key to images

Revision ID: 33aea57b079a
Revises: a1c9f3d8b2e4
Create Date: 2026-08-30 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33aea57b079a'
down_revision: Union[str, Sequence[str], None] = 'a1c9f3d8b2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('images', sa.Column('key', sa.String(length=500), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('images', 'key')
