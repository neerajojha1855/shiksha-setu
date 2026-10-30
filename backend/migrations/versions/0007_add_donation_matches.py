"""add deterministic donation matches"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_add_donation_matches"
down_revision: Union[str, None] = "0006_add_donation_images"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    match_status = postgresql.ENUM(
        "proposed", "accepted", "rejected", "expired",
        name="match_status", create_type=False,
    )
    match_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "donation_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("need_id", sa.Uuid(), nullable=False),
        sa.Column("donation_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("match_factors", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("status", match_status, nullable=False, server_default="proposed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["need_id"], ["school_needs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("need_id", "donation_id", name="uq_donation_matches_need_donation"),
    )
    op.create_index("ix_donation_matches_need_id", "donation_matches", ["need_id"], unique=False)
    op.create_index("ix_donation_matches_donation_id", "donation_matches", ["donation_id"], unique=False)
    op.create_index("ix_donation_matches_status", "donation_matches", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_donation_matches_status", table_name="donation_matches")
    op.drop_index("ix_donation_matches_donation_id", table_name="donation_matches")
    op.drop_index("ix_donation_matches_need_id", table_name="donation_matches")
    op.drop_table("donation_matches")
    sa.Enum("proposed", "accepted", "rejected", "expired", name="match_status").drop(
        op.get_bind(), checkfirst=True
    )
