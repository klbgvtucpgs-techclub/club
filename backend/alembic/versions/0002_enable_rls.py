"""Supabase: turn on Row Level Security for every table.

With RLS on and no policies, Supabase's public REST API (anon/authenticated keys) can read nothing.
This backend connects as the table owner (postgres role), which bypasses RLS, so it keeps working.

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TABLES = ["students", "admins", "clubs", "memberships", "club_counters", "announcements", "photos",
          "email_otps", "pending_registrations", "registration_links", "audit_logs"]


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for t in TABLES:
        op.execute(f'ALTER TABLE public."{t}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for t in TABLES:
        op.execute(f'ALTER TABLE public."{t}" DISABLE ROW LEVEL SECURITY')
