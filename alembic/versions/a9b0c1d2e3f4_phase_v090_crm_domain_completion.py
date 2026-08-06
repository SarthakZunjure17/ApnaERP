"""phase v0.9.0 implement CRM domain completion

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-08-06 12:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a9b0c1d2e3f4'
down_revision = 'f8a9b0c1d2e3'
branch_labels = None
depends_on = None


def upgrade():
    # 1. lead_sources
    op.create_table(
        'lead_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lead_sources_code'), 'lead_sources', ['code'], unique=True)
    op.create_index(op.f('ix_lead_sources_name'), 'lead_sources', ['name'], unique=False)

    # 2. lead_tags
    op.create_table(
        'lead_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('color', sa.String(length=20), server_default='#3B82F6', nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lead_tags_name'), 'lead_tags', ['name'], unique=True)

    # 3. leads
    op.create_table(
        'leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lead_code', sa.String(length=50), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='New', nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_to_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('score', sa.Integer(), server_default='0', nullable=False),
        sa.Column('estimated_value', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('is_converted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('converted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('converted_opportunity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('converted_customer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['converted_customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_id'], ['lead_sources.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leads_assigned_to_id'), 'leads', ['assigned_to_id'], unique=False)
    op.create_index(op.f('ix_leads_company'), 'leads', ['company'], unique=False)
    op.create_index(op.f('ix_leads_email'), 'leads', ['email'], unique=False)
    op.create_index(op.f('ix_leads_first_name'), 'leads', ['first_name'], unique=False)
    op.create_index(op.f('ix_leads_last_name'), 'leads', ['last_name'], unique=False)
    op.create_index(op.f('ix_leads_lead_code'), 'leads', ['lead_code'], unique=True)
    op.create_index(op.f('ix_leads_phone'), 'leads', ['phone'], unique=False)
    op.create_index(op.f('ix_leads_source_id'), 'leads', ['source_id'], unique=False)
    op.create_index(op.f('ix_leads_status'), 'leads', ['status'], unique=False)

    # 4. lead_tags_association
    op.create_table(
        'lead_tags_association',
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['lead_tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('lead_id', 'tag_id')
    )

    # 5. lead_notes
    op.create_table(
        'lead_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_private', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_pinned', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lead_notes_lead_id'), 'lead_notes', ['lead_id'], unique=False)

    # 6. opportunity_stages
    op.create_table(
        'opportunity_stages',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('probability_default', sa.Numeric(precision=5, scale=2), server_default='10.00', nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_opportunity_stages_code'), 'opportunity_stages', ['code'], unique=True)
    op.create_index(op.f('ix_opportunity_stages_name'), 'opportunity_stages', ['name'], unique=False)

    # 7. opportunities
    op.create_table(
        'opportunities',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opportunity_code', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('stage_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expected_revenue', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('probability', sa.Numeric(precision=5, scale=2), server_default='50.00', nullable=False),
        sa.Column('expected_closing_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='Open', nullable=False),
        sa.Column('won_reason', sa.Text(), nullable=True),
        sa.Column('lost_reason', sa.Text(), nullable=True),
        sa.Column('competitors', sa.Text(), nullable=True),
        sa.Column('products_of_interest', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['stage_id'], ['opportunity_stages.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_opportunities_customer_id'), 'opportunities', ['customer_id'], unique=False)
    op.create_index(op.f('ix_opportunities_lead_id'), 'opportunities', ['lead_id'], unique=False)
    op.create_index(op.f('ix_opportunities_opportunity_code'), 'opportunities', ['opportunity_code'], unique=True)
    op.create_index(op.f('ix_opportunities_owner_id'), 'opportunities', ['owner_id'], unique=False)
    op.create_index(op.f('ix_opportunities_stage_id'), 'opportunities', ['stage_id'], unique=False)
    op.create_index(op.f('ix_opportunities_status'), 'opportunities', ['status'], unique=False)
    op.create_index(op.f('ix_opportunities_title'), 'opportunities', ['title'], unique=False)

    # 8. campaigns
    op.create_table(
        'campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('campaign_code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), server_default='Email', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='Planning', nullable=False),
        sa.Column('budget', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('actual_cost', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('expected_revenue', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('actual_revenue', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_campaigns_campaign_code'), 'campaigns', ['campaign_code'], unique=True)
    op.create_index(op.f('ix_campaigns_name'), 'campaigns', ['name'], unique=False)
    op.create_index(op.f('ix_campaigns_owner_id'), 'campaigns', ['owner_id'], unique=False)
    op.create_index(op.f('ix_campaigns_status'), 'campaigns', ['status'], unique=False)
    op.create_index(op.f('ix_campaigns_type'), 'campaigns', ['type'], unique=False)

    # 9. campaign_members
    op.create_table(
        'campaign_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='Invited', nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_campaign_members_campaign_id'), 'campaign_members', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_campaign_members_customer_id'), 'campaign_members', ['customer_id'], unique=False)
    op.create_index(op.f('ix_campaign_members_lead_id'), 'campaign_members', ['lead_id'], unique=False)

    # 10. activities
    op.create_table(
        'activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('activity_type', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='Pending', nullable=False),
        sa.Column('priority', sa.String(length=20), server_default='Medium', nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('opportunity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('recurrence_rule', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activities_activity_type'), 'activities', ['activity_type'], unique=False)
    op.create_index(op.f('ix_activities_campaign_id'), 'activities', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_activities_customer_id'), 'activities', ['customer_id'], unique=False)
    op.create_index(op.f('ix_activities_due_date'), 'activities', ['due_date'], unique=False)
    op.create_index(op.f('ix_activities_lead_id'), 'activities', ['lead_id'], unique=False)
    op.create_index(op.f('ix_activities_opportunity_id'), 'activities', ['opportunity_id'], unique=False)
    op.create_index(op.f('ix_activities_owner_id'), 'activities', ['owner_id'], unique=False)
    op.create_index(op.f('ix_activities_status'), 'activities', ['status'], unique=False)
    op.create_index(op.f('ix_activities_subject'), 'activities', ['subject'], unique=False)

    # 11. meetings
    op.create_table(
        'meetings',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('meeting_type', sa.String(length=50), server_default='Meeting', nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('meeting_link', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='Scheduled', nullable=False),
        sa.Column('organizer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('opportunity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organizer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_meetings_customer_id'), 'meetings', ['customer_id'], unique=False)
    op.create_index(op.f('ix_meetings_lead_id'), 'meetings', ['lead_id'], unique=False)
    op.create_index(op.f('ix_meetings_meeting_type'), 'meetings', ['meeting_type'], unique=False)
    op.create_index(op.f('ix_meetings_opportunity_id'), 'meetings', ['opportunity_id'], unique=False)
    op.create_index(op.f('ix_meetings_organizer_id'), 'meetings', ['organizer_id'], unique=False)
    op.create_index(op.f('ix_meetings_start_time'), 'meetings', ['start_time'], unique=False)
    op.create_index(op.f('ix_meetings_status'), 'meetings', ['status'], unique=False)
    op.create_index(op.f('ix_meetings_subject'), 'meetings', ['subject'], unique=False)

    # 12. crm_tasks
    op.create_table(
        'crm_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('task_code', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='Pending', nullable=False),
        sa.Column('priority', sa.String(length=20), server_default='Medium', nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assigned_to_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('parent_task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('opportunity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_task_id'], ['crm_tasks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crm_tasks_assigned_to_id'), 'crm_tasks', ['assigned_to_id'], unique=False)
    op.create_index(op.f('ix_crm_tasks_campaign_id'), 'crm_tasks', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_crm_tasks_customer_id'), 'crm_tasks', ['customer_id'], unique=False)
    op.create_index(op.f('ix_crm_tasks_due_date'), 'crm_tasks', ['due_date'], unique=False)
    op.create_index(op.f('ix_crm_tasks_lead_id'), 'crm_tasks', ['lead_id'], unique=False)
    op.create_index(op.f('ix_crm_tasks_opportunity_id'), 'crm_tasks', ['opportunity_id'], unique=False)
    op.create_index(op.f('ix_crm_tasks_status'), 'crm_tasks', ['status'], unique=False)
    op.create_index(op.f('ix_crm_tasks_task_code'), 'crm_tasks', ['task_code'], unique=True)
    op.create_index(op.f('ix_crm_tasks_title'), 'crm_tasks', ['title'], unique=False)

    # 13. crm_report_snapshots
    op.create_table(
        'crm_report_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('snapshot_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('period_type', sa.String(length=20), server_default='Daily', nullable=False),
        sa.Column('total_leads', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_opportunities', sa.Integer(), server_default='0', nullable=False),
        sa.Column('forecast_revenue', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('pipeline_value', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('conversion_rate', sa.Numeric(precision=5, scale=2), server_default='0.00', nullable=False),
        sa.Column('metrics_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crm_report_snapshots_snapshot_date'), 'crm_report_snapshots', ['snapshot_date'], unique=False)

    # 14. timeline_events
    op.create_table(
        'timeline_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_timeline_events_entity_id'), 'timeline_events', ['entity_id'], unique=False)
    op.create_index(op.f('ix_timeline_events_entity_type'), 'timeline_events', ['entity_type'], unique=False)
    op.create_index(op.f('ix_timeline_events_event_type'), 'timeline_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_timeline_events_timestamp'), 'timeline_events', ['timestamp'], unique=False)


def downgrade():
    op.drop_table('timeline_events')
    op.drop_table('crm_report_snapshots')
    op.drop_table('crm_tasks')
    op.drop_table('meetings')
    op.drop_table('activities')
    op.drop_table('campaign_members')
    op.drop_table('campaigns')
    op.drop_table('opportunities')
    op.drop_table('opportunity_stages')
    op.drop_table('lead_notes')
    op.drop_table('lead_tags_association')
    op.drop_table('leads')
    op.drop_table('lead_tags')
    op.drop_table('lead_sources')
