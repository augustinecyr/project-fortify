"""add audit_logs table and users.role check constraint

Revision ID: b8d4e2f10a55
Revises: f3a9c1b7d201
Create Date: 2026-06-06 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b8d4e2f10a55'
down_revision: Union[str, Sequence[str], None] = 'f3a9c1b7d201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ROLE_CHECK = "ck_users_role_valid"


def upgrade() -> None:
    """Create the persistent audit trail and constrain role to known values."""
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('event', sa.String(), nullable=False),
        sa.Column('actor', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('target', sa.String(), nullable=True),
        sa.Column('detail', sa.String(), nullable=True),
        sa.Column('ip', sa.String(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_audit_logs_event'), 'audit_logs', ['event'], unique=False)
    op.create_index(op.f('ix_audit_logs_actor'), 'audit_logs', ['actor'], unique=False)

    op.create_check_constraint(
        _ROLE_CHECK, 'users', "role IN ('viewer', 'operator', 'admin')"
    )


def downgrade() -> None:
    """Drop the role constraint and the audit trail."""
    op.drop_constraint(_ROLE_CHECK, 'users', type_='check')
    op.drop_index(op.f('ix_audit_logs_actor'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
