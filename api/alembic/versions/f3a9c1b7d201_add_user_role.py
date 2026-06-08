"""add role column to users

Revision ID: f3a9c1b7d201
Revises: ee5f62a25d2a
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3a9c1b7d201'
down_revision: Union[str, Sequence[str], None] = 'ee5f62a25d2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the RBAC role column.

    New rows default to the least-privileged 'viewer'. Existing accounts are
    backfilled to 'admin' so the migration cannot lock the current operators
    out of the user-management endpoints; down-assign them afterwards.
    """
    op.add_column(
        'users',
        sa.Column('role', sa.String(), nullable=False, server_default='viewer'),
    )
    op.execute("UPDATE users SET role = 'admin'")


def downgrade() -> None:
    """Remove the RBAC role column."""
    op.drop_column('users', 'role')
