"""add press access

Revision ID: b7d2e41c9a10
Revises: a11676007713
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b7d2e41c9a10'
down_revision: Union[str, Sequence[str], None] = 'a11676007713'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('press_access',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('password_hash', sa.String(length=200), nullable=False),
    sa.Column('is_blocked', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_press_access_id'), 'press_access', ['id'], unique=False)
    op.create_index(op.f('ix_press_access_user_id'), 'press_access', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('press_access')
