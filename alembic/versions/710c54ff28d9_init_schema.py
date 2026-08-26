"""init schema

Revision ID: 710c54ff28d9
Revises:
Create Date: 2026-08-26 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '710c54ff28d9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('password_hash', sa.String(length=200), nullable=False),
    sa.Column('slug', sa.String(length=50), nullable=False),
    sa.Column('display_name', sa.String(length=100), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username'),
    sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_slug'), 'users', ['slug'], unique=False)

    op.create_table('youtube',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('video', sa.String(length=200), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_youtube_id'), 'youtube', ['id'], unique=False)
    op.create_index(op.f('ix_youtube_user_id'), 'youtube', ['user_id'], unique=False)

    op.create_table('images',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('tourdates',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('location', sa.String(length=200), nullable=False),
    sa.Column('venue', sa.String(length=200), nullable=False),
    sa.Column('tickets_state', sa.Boolean(), nullable=True),
    sa.Column('tickets_url', sa.String(length=500), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tourdates_id'), 'tourdates', ['id'], unique=False)
    op.create_index(op.f('ix_tourdates_user_id'), 'tourdates', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tourdates_user_id'), table_name='tourdates')
    op.drop_index(op.f('ix_tourdates_id'), table_name='tourdates')
    op.drop_table('tourdates')

    op.drop_table('images')

    op.drop_index(op.f('ix_youtube_user_id'), table_name='youtube')
    op.drop_index(op.f('ix_youtube_id'), table_name='youtube')
    op.drop_table('youtube')

    op.drop_index(op.f('ix_users_slug'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
