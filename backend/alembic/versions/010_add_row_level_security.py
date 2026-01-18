"""Add Row Level Security (RLS) policies for cooptations and job_applications.

Revision ID: 010_add_row_level_security
Revises: 009_add_hr_feature_tables
Create Date: 2026-01-18

This migration enables Row Level Security on sensitive tables to provide
defense-in-depth security. Even if application code has bugs, the database
will enforce access control.

Note: RLS requires setting session variables (app.user_id, app.user_role)
before queries. This is done via middleware in the application.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "010_add_row_level_security"
down_revision = "009_add_hr_feature_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable RLS and create security policies."""

    # ===========================================
    # COOPTATIONS TABLE RLS
    # ===========================================

    # Enable RLS on cooptations table
    op.execute("ALTER TABLE cooptations ENABLE ROW LEVEL SECURITY;")

    # Drop existing policies first (idempotent)
    op.execute("DROP POLICY IF EXISTS cooptations_own_select ON cooptations;")
    op.execute("DROP POLICY IF EXISTS cooptations_own_insert ON cooptations;")
    op.execute("DROP POLICY IF EXISTS cooptations_own_update ON cooptations;")
    op.execute("DROP POLICY IF EXISTS cooptations_commercial_select ON cooptations;")
    op.execute("DROP POLICY IF EXISTS cooptations_admin_rh_all ON cooptations;")

    # Policy: Users can see their own cooptations (submitter_id = current user)
    op.execute("""
        CREATE POLICY cooptations_own_select ON cooptations
            FOR SELECT
            USING (
                submitter_id::text = current_setting('app.user_id', true)
            );
    """)

    # Policy: Users can insert their own cooptations
    op.execute("""
        CREATE POLICY cooptations_own_insert ON cooptations
            FOR INSERT
            WITH CHECK (
                submitter_id::text = current_setting('app.user_id', true)
            );
    """)

    # Policy: Users can update their own cooptations (limited fields in app)
    op.execute("""
        CREATE POLICY cooptations_own_update ON cooptations
            FOR UPDATE
            USING (
                submitter_id::text = current_setting('app.user_id', true)
            );
    """)

    # Policy: Commercials can see all cooptations (they manage opportunities)
    # Note: We allow all cooptations for commercials since opportunity ownership
    # is managed at the application level via BoondManager
    op.execute("""
        CREATE POLICY cooptations_commercial_select ON cooptations
            FOR SELECT
            USING (
                current_setting('app.user_role', true) = 'commercial'
            );
    """)

    # Policy: Admin and RH can see all cooptations
    op.execute("""
        CREATE POLICY cooptations_admin_rh_all ON cooptations
            FOR ALL
            USING (
                current_setting('app.user_role', true) IN ('admin', 'rh')
            );
    """)

    # ===========================================
    # JOB_APPLICATIONS TABLE RLS
    # ===========================================

    # Enable RLS on job_applications table
    op.execute("ALTER TABLE job_applications ENABLE ROW LEVEL SECURITY;")

    # Drop existing policies first (idempotent)
    op.execute("DROP POLICY IF EXISTS job_applications_admin_rh_all ON job_applications;")
    op.execute("DROP POLICY IF EXISTS job_applications_public_insert ON job_applications;")

    # Policy: Admin and RH can see all applications
    op.execute("""
        CREATE POLICY job_applications_admin_rh_all ON job_applications
            FOR ALL
            USING (
                current_setting('app.user_role', true) IN ('admin', 'rh')
            );
    """)

    # Policy: Public can insert applications (no auth check for INSERT)
    # This allows the public application form to work
    op.execute("""
        CREATE POLICY job_applications_public_insert ON job_applications
            FOR INSERT
            WITH CHECK (true);
    """)

    # ===========================================
    # CV_TRANSFORMATION_LOGS TABLE RLS
    # ===========================================

    # Enable RLS on cv_transformation_logs table
    op.execute("ALTER TABLE cv_transformation_logs ENABLE ROW LEVEL SECURITY;")

    # Drop existing policies first (idempotent)
    op.execute("DROP POLICY IF EXISTS cv_logs_own_select ON cv_transformation_logs;")
    op.execute("DROP POLICY IF EXISTS cv_logs_own_insert ON cv_transformation_logs;")
    op.execute("DROP POLICY IF EXISTS cv_logs_admin_all ON cv_transformation_logs;")

    # Policy: Users can see their own transformation logs
    op.execute("""
        CREATE POLICY cv_logs_own_select ON cv_transformation_logs
            FOR SELECT
            USING (
                user_id::text = current_setting('app.user_id', true)
            );
    """)

    # Policy: Users can insert their own logs
    op.execute("""
        CREATE POLICY cv_logs_own_insert ON cv_transformation_logs
            FOR INSERT
            WITH CHECK (
                user_id::text = current_setting('app.user_id', true)
            );
    """)

    # Policy: Admin can see all logs (for stats)
    op.execute("""
        CREATE POLICY cv_logs_admin_all ON cv_transformation_logs
            FOR ALL
            USING (
                current_setting('app.user_role', true) = 'admin'
            );
    """)

    # ===========================================
    # BYPASS POLICY FOR SUPERUSER/SERVICE ROLE
    # ===========================================
    # Note: By default, table owners and superusers bypass RLS.
    # For service accounts that need full access, you can:
    # ALTER USER service_account BYPASSRLS;

    # Create a function to set the app context
    op.execute("""
        CREATE OR REPLACE FUNCTION set_app_context(
            p_user_id text,
            p_user_role text
        ) RETURNS void AS $$
        BEGIN
            PERFORM set_config('app.user_id', p_user_id, true);
            PERFORM set_config('app.user_role', p_user_role, true);
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create a function to clear the app context
    op.execute("""
        CREATE OR REPLACE FUNCTION clear_app_context() RETURNS void AS $$
        BEGIN
            PERFORM set_config('app.user_id', '', true);
            PERFORM set_config('app.user_role', '', true);
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """Remove RLS and policies."""

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS set_app_context(text, text);")
    op.execute("DROP FUNCTION IF EXISTS clear_app_context();")

    # Drop cv_transformation_logs policies and disable RLS
    op.execute("DROP POLICY IF EXISTS cv_logs_own_select ON cv_transformation_logs;")
    op.execute("DROP POLICY IF EXISTS cv_logs_own_insert ON cv_transformation_logs;")
    op.execute("DROP POLICY IF EXISTS cv_logs_admin_all ON cv_transformation_logs;")
    op.execute("ALTER TABLE cv_transformation_logs DISABLE ROW LEVEL SECURITY;")

    # Drop job_applications policies and disable RLS
    op.execute("DROP POLICY IF EXISTS job_applications_admin_rh_all ON job_applications;")
    op.execute("DROP POLICY IF EXISTS job_applications_public_insert ON job_applications;")
    op.execute("ALTER TABLE job_applications DISABLE ROW LEVEL SECURITY;")

    # Drop cooptations policies and disable RLS
    op.execute("DROP POLICY IF EXISTS cooptations_own_select ON cooptations;")
    op.execute("DROP POLICY IF EXISTS cooptations_own_insert ON cooptations;")
    op.execute("DROP POLICY IF EXISTS cooptations_own_update ON cooptations;")
    op.execute("DROP POLICY IF EXISTS cooptations_commercial_select ON cooptations;")
    op.execute("DROP POLICY IF EXISTS cooptations_admin_rh_all ON cooptations;")
    op.execute("ALTER TABLE cooptations DISABLE ROW LEVEL SECURITY;")
