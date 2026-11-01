"""add distribution workflow and transition history"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009_add_distributions"
down_revision: Union[str, None] = "0008_add_donation_reservations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    distribution_status = postgresql.ENUM(
        "reserved", "in_transit", "delivered_pending_confirmation", "received",
        "verified", "cancelled", "rejected",
        name="distribution_status", create_type=False,
    )
    distribution_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "distributions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("delivery_method", sa.String(length=80), nullable=True),
        sa.Column("tracking_reference", sa.String(length=160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", distribution_status, nullable=False, server_default="reserved"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["reservation_id"], ["donation_reservations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id"),
    )
    op.create_index("ix_distributions_reservation_id", "distributions", ["reservation_id"], unique=True)
    op.create_index("ix_distributions_status", "distributions", ["status"], unique=False)

    op.create_table(
        "distribution_transitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("distribution_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", distribution_status, nullable=True),
        sa.Column("to_status", distribution_status, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["distribution_id"], ["distributions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_distribution_transitions_distribution_id", "distribution_transitions", ["distribution_id"], unique=False)
    op.create_index("ix_distribution_transitions_actor_id", "distribution_transitions", ["actor_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_distribution_transitions_actor_id", table_name="distribution_transitions")
    op.drop_index("ix_distribution_transitions_distribution_id", table_name="distribution_transitions")
    op.drop_table("distribution_transitions")
    op.drop_index("ix_distributions_status", table_name="distributions")
    op.drop_index("ix_distributions_reservation_id", table_name="distributions")
    op.drop_table("distributions")
    sa.Enum(
        "reserved", "in_transit", "delivered_pending_confirmation", "received",
        "verified", "cancelled", "rejected", name="distribution_status"
    ).drop(op.get_bind(), checkfirst=True)
