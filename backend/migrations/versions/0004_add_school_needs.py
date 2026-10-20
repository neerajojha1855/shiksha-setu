"""add school needs registry"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_add_school_needs"
down_revision: Union[str, None] = "0003_add_school_onboarding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    need_status = postgresql.ENUM(
        "draft", "published", "paused", "closed", name="need_status", create_type=False
    )
    need_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "school_needs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("quantity_requested", sa.Integer(), nullable=False),
        sa.Column("quantity_fulfilled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("condition", sa.String(length=80), nullable=False),
        sa.Column("urgency", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False),
        sa.Column("intended_use", sa.Text(), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("status", need_status, nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("school_id", "category", "urgency", "priority", "city", "region", "status"):
        op.create_index(f"ix_school_needs_{column}", "school_needs", [column], unique=False)


def downgrade() -> None:
    for column in ("status", "region", "city", "priority", "urgency", "category", "school_id"):
        op.drop_index(f"ix_school_needs_{column}", table_name="school_needs")
    op.drop_table("school_needs")
    sa.Enum("draft", "published", "paused", "closed", name="need_status").drop(
        op.get_bind(), checkfirst=True
    )
