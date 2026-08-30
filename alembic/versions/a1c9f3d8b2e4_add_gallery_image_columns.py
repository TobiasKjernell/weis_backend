"""add gallery image columns

Revision ID: a1c9f3d8b2e4
Revises: 3e2e98ad04ad
Create Date: 2026-08-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c9f3d8b2e4'
down_revision: Union[str, Sequence[str], None] = '3e2e98ad04ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('images', sa.Column('url', sa.String(length=500), nullable=False))
    op.add_column('images', sa.Column('position', sa.Integer(), nullable=False))
    op.add_column('images', sa.Column('user_id', sa.Integer(), nullable=False))
    op.create_index(op.f('ix_images_id'), 'images', ['id'], unique=False)
    op.create_index(op.f('ix_images_user_id'), 'images', ['user_id'], unique=False)
    op.create_foreign_key(op.f('images_user_id_fkey'), 'images', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('images_user_id_fkey'), 'images', type_='foreignkey')
    op.drop_index(op.f('ix_images_user_id'), table_name='images')
    op.drop_index(op.f('ix_images_id'), table_name='images')
    op.drop_column('images', 'user_id')
    op.drop_column('images', 'position')
    op.drop_column('images', 'url')
