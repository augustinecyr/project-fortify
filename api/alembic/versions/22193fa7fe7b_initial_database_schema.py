"""initial database schema

Revision ID: 22193fa7fe7b
Revises:
Create Date: 2026-01-31 12:02:04.877246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22193fa7fe7b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('virtual_machines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vm_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('host', sa.String(), nullable=True),
        sa.Column('os_version', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('uptime_hours', sa.Float(), nullable=True),
        sa.Column('last_boot_time', sa.DateTime(), nullable=True),
        sa.Column('health_score', sa.Integer(), nullable=True),
        sa.Column('security_score', sa.Integer(), nullable=True),
        sa.Column('current_cpu', sa.Float(), nullable=True),
        sa.Column('current_memory', sa.Float(), nullable=True),
        sa.Column('current_disk', sa.Float(), nullable=True),
        sa.Column('memory_total_mb', sa.Integer(), nullable=True),
        sa.Column('memory_used_mb', sa.Integer(), nullable=True),
        sa.Column('disk_total_gb', sa.Integer(), nullable=True),
        sa.Column('disk_used_gb', sa.Integer(), nullable=True),
        sa.Column('network_in_mbps', sa.Float(), nullable=True),
        sa.Column('network_out_mbps', sa.Float(), nullable=True),
        sa.Column('last_patch_date', sa.DateTime(), nullable=True),
        sa.Column('open_vulnerabilities', sa.Integer(), nullable=True),
        sa.Column('critical_vulnerabilities', sa.Integer(), nullable=True),
        sa.Column('compliance_score', sa.String(), nullable=True),
        sa.Column('firewall_enabled', sa.Boolean(), nullable=True),
        sa.Column('ssh_key_auth', sa.Boolean(), nullable=True),
        sa.Column('disk_encryption', sa.Boolean(), nullable=True),
        sa.Column('alert_count', sa.Integer(), nullable=True),
        sa.Column('anomaly_detected', sa.Boolean(), nullable=True),
        sa.Column('last_anomaly_time', sa.DateTime(), nullable=True),
        sa.Column('avg_cpu_24h', sa.Float(), nullable=True),
        sa.Column('avg_memory_24h', sa.Float(), nullable=True),
        sa.Column('avg_disk_24h', sa.Float(), nullable=True),
        sa.Column('peak_cpu_24h', sa.Float(), nullable=True),
        sa.Column('metric_count_24h', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_virtual_machines_id', 'virtual_machines', ['id'], unique=False)
    op.create_index('ix_virtual_machines_vm_id', 'virtual_machines', ['vm_id'], unique=True)
    op.create_index('idx_vm_host', 'virtual_machines', ['host'], unique=False)
    op.create_index('idx_vm_status', 'virtual_machines', ['status'], unique=False)
    op.create_index('idx_vm_health_score', 'virtual_machines', ['health_score'], unique=False)
    op.create_index('idx_vm_security_score', 'virtual_machines', ['security_score'], unique=False)

    op.create_table('cpu_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vm_id', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('cpu_percent', sa.Float(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['vm_id'], ['virtual_machines.vm_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cpu_metrics_id', 'cpu_metrics', ['id'], unique=False)
    op.create_index('ix_cpu_metrics_vm_id', 'cpu_metrics', ['vm_id'], unique=False)
    op.create_index('ix_cpu_metrics_timestamp', 'cpu_metrics', ['timestamp'], unique=False)

    op.create_table('health_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vm_id', sa.String(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('computed_at', sa.DateTime(), nullable=True),
        sa.Column('components', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['vm_id'], ['virtual_machines.vm_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_health_scores_id', 'health_scores', ['id'], unique=False)
    op.create_index('ix_health_scores_vm_id', 'health_scores', ['vm_id'], unique=False)
    op.create_index('ix_health_scores_computed_at', 'health_scores', ['computed_at'], unique=False)

    op.create_table('memory_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vm_id', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('memory_percent', sa.Float(), nullable=False),
        sa.Column('memory_used_mb', sa.Integer(), nullable=True),
        sa.Column('memory_total_mb', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['vm_id'], ['virtual_machines.vm_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_memory_timestamp', 'memory_metrics', ['timestamp'], unique=False)
    op.create_index('idx_memory_vm_id', 'memory_metrics', ['vm_id'], unique=False)
    op.create_index('idx_memory_vm_timestamp', 'memory_metrics', ['vm_id', 'timestamp'], unique=False)


def downgrade() -> None:
    op.drop_table('memory_metrics')
    op.drop_table('health_scores')
    op.drop_table('cpu_metrics')
    op.drop_table('virtual_machines')
