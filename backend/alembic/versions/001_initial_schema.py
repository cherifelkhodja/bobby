"""Initial schema creation

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-01-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='member'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('boond_resource_id', sa.String(50), nullable=True),
        sa.Column('verification_token', sa.String(255), nullable=True),
        sa.Column('reset_token', sa.String(255), nullable=True),
        sa.Column('reset_token_expires', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create candidates table
    op.create_table(
        'candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('civility', sa.String(10), nullable=False, server_default='M'),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('cv_filename', sa.String(255), nullable=True),
        sa.Column('cv_path', sa.String(500), nullable=True),
        sa.Column('daily_rate', sa.Float(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('external_id', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_candidates_email', 'candidates', ['email'], unique=False)
    op.create_index('ix_candidates_external_id', 'candidates', ['external_id'], unique=False)

    # Create opportunities table
    op.create_table(
        'opportunities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('external_id', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('reference', sa.String(100), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('response_deadline', sa.Date(), nullable=True),
        sa.Column('budget', sa.Float(), nullable=True),
        sa.Column('manager_name', sa.String(200), nullable=True),
        sa.Column('manager_email', sa.String(255), nullable=True),
        sa.Column('client_name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('skills', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('location', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('synced_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id')
    )
    op.create_index('ix_opportunities_external_id', 'opportunities', ['external_id'], unique=True)

    # Create cooptations table
    op.create_table(
        'cooptations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('opportunity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('submitter_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('external_positioning_id', sa.String(50), nullable=True),
        sa.Column('status_history', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], name='fk_cooptations_candidate'),
        sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], name='fk_cooptations_opportunity'),
        sa.ForeignKeyConstraint(['submitter_id'], ['users.id'], name='fk_cooptations_submitter')
    )
    op.create_index('ix_cooptations_status', 'cooptations', ['status'], unique=False)
    op.create_index('ix_cooptations_candidate_id', 'cooptations', ['candidate_id'], unique=False)
    op.create_index('ix_cooptations_opportunity_id', 'cooptations', ['opportunity_id'], unique=False)
    op.create_index('ix_cooptations_submitter_id', 'cooptations', ['submitter_id'], unique=False)


def downgrade() -> None:
    # Drop cooptations table first (has foreign keys)
    op.drop_index('ix_cooptations_submitter_id', table_name='cooptations')
    op.drop_index('ix_cooptations_opportunity_id', table_name='cooptations')
    op.drop_index('ix_cooptations_candidate_id', table_name='cooptations')
    op.drop_index('ix_cooptations_status', table_name='cooptations')
    op.drop_table('cooptations')

    # Drop opportunities table
    op.drop_index('ix_opportunities_external_id', table_name='opportunities')
    op.drop_table('opportunities')

    # Drop candidates table
    op.drop_index('ix_candidates_external_id', table_name='candidates')
    op.drop_index('ix_candidates_email', table_name='candidates')
    op.drop_table('candidates')

    # Drop users table
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
