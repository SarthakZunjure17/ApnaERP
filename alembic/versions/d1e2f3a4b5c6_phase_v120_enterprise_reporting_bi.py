"""phase_v120_enterprise_reporting_bi

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-08-07 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Dashboards
    op.create_table(
        'dashboards',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dashboard_type', sa.String(length=50), server_default='Custom', nullable=False),
        sa.Column('is_system', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_shared', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('layout_config', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_dashboards_code'), 'dashboards', ['code'], unique=True)
    op.create_index(op.f('ix_dashboards_dashboard_type'), 'dashboards', ['dashboard_type'], unique=False)
    op.create_index(op.f('ix_dashboards_is_system'), 'dashboards', ['is_system'], unique=False)
    op.create_index(op.f('ix_dashboards_owner_id'), 'dashboards', ['owner_id'], unique=False)

    # 2. KPIs
    op.create_table(
        'kpis',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('module', sa.String(length=50), nullable=False),
        sa.Column('calculation_type', sa.String(length=50), server_default='SystemQuery', nullable=False),
        sa.Column('formula', sa.Text(), nullable=True),
        sa.Column('unit', sa.String(length=30), server_default='Count', nullable=False),
        sa.Column('target_value', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('warning_threshold', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('critical_threshold', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('refresh_interval_minutes', sa.Integer(), server_default='60', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_kpis_code'), 'kpis', ['code'], unique=True)
    op.create_index(op.f('ix_kpis_name'), 'kpis', ['name'], unique=False)
    op.create_index(op.f('ix_kpis_module'), 'kpis', ['module'], unique=False)
    op.create_index(op.f('ix_kpis_is_active'), 'kpis', ['is_active'], unique=False)

    # 3. KPIMetrics
    op.create_table(
        'kpi_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('kpi_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_value', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('dimensions_json', postgresql.JSONB(), nullable=True),
        sa.Column('trend_status', sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(['kpi_id'], ['kpis.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kpi_metrics_kpi_id'), 'kpi_metrics', ['kpi_id'], unique=False)
    op.create_index(op.f('ix_kpi_metrics_recorded_at'), 'kpi_metrics', ['recorded_at'], unique=False)

    # 4. ReportTemplates
    op.create_table(
        'report_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('module', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('datasource_key', sa.String(length=100), nullable=False),
        sa.Column('default_columns', postgresql.JSONB(), nullable=False),
        sa.Column('default_filters', postgresql.JSONB(), nullable=True),
        sa.Column('default_sorting', postgresql.JSONB(), nullable=True),
        sa.Column('is_system', sa.Boolean(), server_default='true', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_report_templates_code'), 'report_templates', ['code'], unique=True)
    op.create_index(op.f('ix_report_templates_name'), 'report_templates', ['name'], unique=False)
    op.create_index(op.f('ix_report_templates_module'), 'report_templates', ['module'], unique=False)
    op.create_index(op.f('ix_report_templates_is_system'), 'report_templates', ['is_system'], unique=False)

    # 5. SavedReports
    op.create_table(
        'saved_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_shared', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('selected_columns', postgresql.JSONB(), nullable=False),
        sa.Column('applied_filters', postgresql.JSONB(), nullable=True),
        sa.Column('sorting_rules', postgresql.JSONB(), nullable=True),
        sa.Column('grouping_rules', postgresql.JSONB(), nullable=True),
        sa.Column('calculated_fields', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['template_id'], ['report_templates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_saved_reports_template_id'), 'saved_reports', ['template_id'], unique=False)
    op.create_index(op.f('ix_saved_reports_name'), 'saved_reports', ['name'], unique=False)
    op.create_index(op.f('ix_saved_reports_owner_id'), 'saved_reports', ['owner_id'], unique=False)

    # 6. ScheduledReports
    op.create_table(
        'scheduled_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('saved_report_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('frequency', sa.String(length=30), server_default='Weekly', nullable=False),
        sa.Column('cron_expression', sa.String(length=100), nullable=True),
        sa.Column('export_format', sa.String(length=20), server_default='PDF', nullable=False),
        sa.Column('recipients', postgresql.JSONB(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['saved_report_id'], ['saved_reports.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['template_id'], ['report_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scheduled_reports_saved_report_id'), 'scheduled_reports', ['saved_report_id'], unique=False)
    op.create_index(op.f('ix_scheduled_reports_owner_id'), 'scheduled_reports', ['owner_id'], unique=False)
    op.create_index(op.f('ix_scheduled_reports_is_active'), 'scheduled_reports', ['is_active'], unique=False)

    # 7. ChartConfigurations
    op.create_table(
        'chart_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('chart_type', sa.String(length=50), nullable=False),
        sa.Column('module', sa.String(length=50), nullable=False),
        sa.Column('x_axis_field', sa.String(length=100), nullable=False),
        sa.Column('y_axis_fields', postgresql.JSONB(), nullable=False),
        sa.Column('series_config', postgresql.JSONB(), nullable=True),
        sa.Column('color_palette', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_chart_configurations_code'), 'chart_configurations', ['code'], unique=True)
    op.create_index(op.f('ix_chart_configurations_chart_type'), 'chart_configurations', ['chart_type'], unique=False)
    op.create_index(op.f('ix_chart_configurations_module'), 'chart_configurations', ['module'], unique=False)

    # 8. DashboardWidgets
    op.create_table(
        'dashboard_widgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('dashboard_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('widget_type', sa.String(length=50), nullable=False),
        sa.Column('kpi_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('chart_config_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('report_template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('grid_position', postgresql.JSONB(), nullable=False),
        sa.Column('settings_json', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['chart_config_id'], ['chart_configurations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['dashboard_id'], ['dashboards.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['kpi_id'], ['kpis.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['report_template_id'], ['report_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dashboard_widgets_dashboard_id'), 'dashboard_widgets', ['dashboard_id'], unique=False)

    # 9. ReportExecutions
    op.create_table(
        'report_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('scheduled_report_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('saved_report_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('executed_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=30), server_default='Completed', nullable=False),
        sa.Column('export_format', sa.String(length=20), server_default='PDF', nullable=False),
        sa.Column('export_file_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('row_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['executed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['export_file_id'], ['files.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['saved_report_id'], ['saved_reports.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['scheduled_report_id'], ['scheduled_reports.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['template_id'], ['report_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_report_executions_scheduled_report_id'), 'report_executions', ['scheduled_report_id'], unique=False)
    op.create_index(op.f('ix_report_executions_status'), 'report_executions', ['status'], unique=False)

    # 10. AnalyticsSnapshots
    op.create_table(
        'analytics_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('snapshot_type', sa.String(length=50), nullable=False),
        sa.Column('module', sa.String(length=50), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('metrics_json', postgresql.JSONB(), nullable=False),
        sa.Column('dimensions_json', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analytics_snapshots_snapshot_type'), 'analytics_snapshots', ['snapshot_type'], unique=False)
    op.create_index(op.f('ix_analytics_snapshots_module'), 'analytics_snapshots', ['module'], unique=False)
    op.create_index(op.f('ix_analytics_snapshots_period_start'), 'analytics_snapshots', ['period_start'], unique=False)
    op.create_index(op.f('ix_analytics_snapshots_period_end'), 'analytics_snapshots', ['period_end'], unique=False)


def downgrade() -> None:
    op.drop_table('analytics_snapshots')
    op.drop_table('report_executions')
    op.drop_table('dashboard_widgets')
    op.drop_table('chart_configurations')
    op.drop_table('scheduled_reports')
    op.drop_table('saved_reports')
    op.drop_table('report_templates')
    op.drop_table('kpi_metrics')
    op.drop_table('kpis')
    op.drop_table('dashboards')
