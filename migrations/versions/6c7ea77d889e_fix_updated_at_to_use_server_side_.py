"""Fix updated_at to use server-side trigger for automatic updates

Revision ID: 6c7ea77d889e
Revises: a34c4bcee4ff
Create Date: 2026-03-20 03:44:57.756113

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6c7ea77d889e"
down_revision: Union[str, Sequence[str], None] = "a34c4bcee4ff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create a reusable trigger function that sets updated_at to NOW()
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Create trigger on users table
    op.execute(
        """
        CREATE TRIGGER set_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
        """
    )

    # Create trigger on roles table
    op.execute(
        """
        CREATE TRIGGER set_roles_updated_at
            BEFORE UPDATE ON roles
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS set_users_updated_at ON users")
    op.execute("DROP TRIGGER IF EXISTS set_roles_updated_at ON roles")

    # Drop the trigger function
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
