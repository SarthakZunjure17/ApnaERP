"""phase_hr2_implement_employees_table

Revision ID: d04dad64b43e
Revises: 'd45778acc419'
Create Date: 2026-07-26 15:21:47.165896+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd04dad64b43e'
down_revision: Union[str, None] = 'd45778acc419'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('employees',
    sa.Column('employee_code', sa.String(length=50), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('middle_name', sa.String(length=100), nullable=True),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('preferred_name', sa.String(length=100), nullable=True),
    sa.Column('work_email', sa.String(length=255), nullable=False),
    sa.Column('personal_email', sa.String(length=255), nullable=True),
    sa.Column('work_phone', sa.String(length=50), nullable=True),
    sa.Column('personal_phone', sa.String(length=50), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('manager_id', sa.UUID(), nullable=True),
    sa.Column('employment_type', sa.String(length=50), nullable=False),
    sa.Column('employment_status', sa.String(length=50), nullable=False),
    sa.Column('joining_date', sa.Date(), nullable=False),
    sa.Column('confirmation_date', sa.Date(), nullable=True),
    sa.Column('exit_date', sa.Date(), nullable=True),
    sa.Column('date_of_birth', sa.Date(), nullable=True),
    sa.Column('gender', sa.String(length=20), nullable=True),
    sa.Column('profile_photo_file_id', sa.UUID(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False, comment='Primary Key UUID'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record creation timestamp (UTC)'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record last update timestamp (UTC)'),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False, comment='Soft deletion flag'),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when record was soft-deleted (UTC)'),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_employees_department_id_departments'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['manager_id'], ['employees.id'], name=op.f('fk_employees_manager_id_employees'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['profile_photo_file_id'], ['files.id'], name=op.f('fk_employees_profile_photo_file_id_files'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_employees_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_employees'))
    )
    op.create_index(op.f('ix_employees_department_id'), 'employees', ['department_id'], unique=False)
    op.create_index(op.f('ix_employees_employee_code'), 'employees', ['employee_code'], unique=True)
    op.create_index(op.f('ix_employees_id'), 'employees', ['id'], unique=False)
    op.create_index(op.f('ix_employees_is_deleted'), 'employees', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_employees_manager_id'), 'employees', ['manager_id'], unique=False)
    op.create_index(op.f('ix_employees_profile_photo_file_id'), 'employees', ['profile_photo_file_id'], unique=False)
    op.create_index(op.f('ix_employees_user_id'), 'employees', ['user_id'], unique=True)
    op.create_index(op.f('ix_employees_work_email'), 'employees', ['work_email'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_employees_work_email'), table_name='employees')
    op.drop_index(op.f('ix_employees_user_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_profile_photo_file_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_manager_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_is_deleted'), table_name='employees')
    op.drop_index(op.f('ix_employees_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_employee_code'), table_name='employees')
    op.drop_index(op.f('ix_employees_department_id'), table_name='employees')
    op.drop_table('employees')
