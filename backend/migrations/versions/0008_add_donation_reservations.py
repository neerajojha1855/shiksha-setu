"""add transactional donation reservations"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_add_donation_reservations"
down_revision: Union[str, None] = "0007_add_donation_matches"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    reservation_status = postgresql.ENUM(
        "reserved", "released", "fulfilled", "cancelled",
        name="reservation_status", create_type=False,
    )
    reservation_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "donation_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", reservation_status, nullable=False, server_default="reserved"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["donation_matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id"),
    )
    op.create_index("ix_donation_reservations_match_id", "donation_reservations", ["match_id"], unique=True)
    op.create_index("ix_donation_reservations_status", "donation_reservations", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_donation_reservations_status", table_name="donation_reservations")
    op.drop_index("ix_donation_reservations_match_id", table_name="donation_reservations")
    op.drop_table("donation_reservations")
    sa.Enum(
        "reserved", "released", "fulfilled", "cancelled", name="reservation_status"
    ).drop(op.get_bind(), checkfirst=True)
