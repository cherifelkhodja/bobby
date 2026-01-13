"""Add new roles, invitations and business leads tables

Revision ID: 002_add_roles_invites
Revises: 001_initial_schema
Create Date: 2026-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_roles_invites'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update users table: add manager_boond_id and change default role
    op.add_column('users', sa.Column('manager_boond_id', sa.String(50), nullable=True))

    # Update default role from 'member' to 'user' (for new users)
    # Existing 'member' users will remain as 'member' until migrated
    op.execute("UPDATE users SET role = 'user' WHERE role = 'member'")

    # Update opportunities table: add manager_boond_id, is_shared, owner_id
    op.add_column('opportunities', sa.Column('manager_boond_id', sa.String(50), nullable=True))
    op.add_column('opportunities', sa.Column('is_shared', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('opportunities', sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True))

    op.create_index('ix_opportunities_manager_boond_id', 'opportunities', ['manager_boond_id'], unique=False)
    op.create_index('ix_opportunities_owner_id', 'opportunities', ['owner_id'], unique=False)
    op.create_foreign_key(
        'fk_opportunities_owner',
        'opportunities', 'users',
        ['owner_id'], ['id'],
        ondelete='SET NULL'
    )

    # Create invitations table
    op.create_table(
        'invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='user'),
        sa.Column('token', sa.String(255), nullable=False),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], name='fk_invitations_inviter'),
        sa.UniqueConstraint('token')
    )
    op.create_index('ix_invitations_email', 'invitations', ['email'], unique=False)
    op.create_index('ix_invitations_token', 'invitations', ['token'], unique=True)

    # Create business_leads table
    op.create_table(
        'business_leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('submitter_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_name', sa.String(200), nullable=False),
        sa.Column('contact_name', sa.String(200), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(20), nullable=True),
        sa.Column('estimated_budget', sa.Float(), nullable=True),
        sa.Column('expected_start_date', sa.Date(), nullable=True),
        sa.Column('skills_needed', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('location', sa.String(200), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['submitter_id'], ['users.id'], name='fk_business_leads_submitter')
    )
    op.create_index('ix_business_leads_status', 'business_leads', ['status'], unique=False)
    op.create_index('ix_business_leads_submitter_id', 'business_leads', ['submitter_id'], unique=False)


def downgrade() -> None:
    # Drop business_leads table
    op.drop_index('ix_business_leads_submitter_id', table_name='business_leads')
    op.drop_index('ix_business_leads_status', table_name='business_leads')
    op.drop_table('business_leads')

    # Drop invitations table
    op.drop_index('ix_invitations_token', table_name='invitations')
    op.drop_index('ix_invitations_email', table_name='invitations')
    op.drop_table('invitations')

    # Revert opportunities changes
    op.drop_constraint('fk_opportunities_owner', 'opportunities', type_='foreignkey')
    op.drop_index('ix_opportunities_owner_id', table_name='opportunities')
    op.drop_index('ix_opportunities_manager_boond_id', table_name='opportunities')
    op.drop_column('opportunities', 'owner_id')
    op.drop_column('opportunities', 'is_shared')
    op.drop_column('opportunities', 'manager_boond_id')

    # Revert users changes
    op.execute("UPDATE users SET role = 'member' WHERE role = 'user'")
    op.drop_column('users', 'manager_boond_id')
