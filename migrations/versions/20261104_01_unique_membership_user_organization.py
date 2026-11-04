"""Add uniqueness for user memberships within an organization.

Revision ID: 20261104_01
Revises: None
"""
from alembic import op
import sqlalchemy as sa

revision = "20261104_01"
down_revision = None
branch_labels = None
depends_on = None


CONSTRAINT_NAME = "uq_memberships_user_organization"


def upgrade() -> None:
    bind = op.get_bind()
    duplicate = bind.execute(
        sa.text(
            """
            SELECT user_id, organization_id, COUNT(*) AS duplicate_count
            FROM memberships
            GROUP BY user_id, organization_id
            HAVING COUNT(*) > 1
            ORDER BY user_id, organization_id
            LIMIT 1
            """
        )
    ).first()

    if duplicate is not None:
        raise RuntimeError(
            "Cannot add membership uniqueness constraint: duplicate rows exist "
            f"for user_id={duplicate.user_id}, "
            f"organization_id={duplicate.organization_id} "
            f"(count={duplicate.duplicate_count}). Resolve duplicates without "
            "deleting membership data, then rerun the migration."
        )

    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "memberships",
        ["user_id", "organization_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        CONSTRAINT_NAME,
        "memberships",
        type_="unique",
    )
