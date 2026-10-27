"""add donor profiles and donation listings"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_add_donations"
down_revision: Union[str, None] = "0004_add_school_needs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    donation_status = postgresql.ENUM("active", "withdrawn", name="donation_status", create_type=False)
    donation_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "donor_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("organization", sa.String(length=160)),
        sa.Column("bio", sa.Text()),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id"),
    )
    op.create_index("ix_donor_profiles_owner_id", "donor_profiles", ["owner_id"], unique=True)
    op.create_table(
        "donations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("donor_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("quantity_available", sa.Integer(), nullable=False),
        sa.Column("quantity_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("condition", sa.String(length=80), nullable=False),
        sa.Column("availability", sa.String(length=80), nullable=False),
        sa.Column("pickup_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("delivery_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("status", donation_status, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["donor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("donor_id", "category", "city", "region", "status"):
        op.create_index(f"ix_donations_{column}", "donations", [column], unique=False)


def downgrade() -> None:
    for column in ("status", "region", "city", "category", "donor_id"):
        op.drop_index(f"ix_donations_{column}", table_name="donations")
    op.drop_table("donations")
    op.drop_index("ix_donor_profiles_owner_id", table_name="donor_profiles")
    op.drop_table("donor_profiles")
    sa.Enum("active", "withdrawn", name="donation_status").drop(op.get_bind(), checkfirst=True)
