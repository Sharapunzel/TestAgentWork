"""Create log imports and entries tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260921_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "log_imports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_lines", sa.Integer(), nullable=False),
        sa.Column("accepted_lines", sa.Integer(), nullable=False),
        sa.Column("rejected_lines", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(), nullable=True),
        sa.CheckConstraint(
            "accepted_lines >= 0", name="ck_log_imports_accepted_lines"
        ),
        sa.CheckConstraint(
            "rejected_lines >= 0", name="ck_log_imports_rejected_lines"
        ),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'failed')",
            name="ck_log_imports_status",
        ),
        sa.CheckConstraint("total_lines >= 0", name="ck_log_imports_total_lines"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "log_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("import_id", sa.String(length=36), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("remote_addr", sa.String(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("request_path", sa.String(), nullable=False),
        sa.Column("request_protocol", sa.String(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("body_bytes_sent", sa.Integer(), nullable=False),
        sa.Column("referer", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("raw_line", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "body_bytes_sent >= 0", name="ck_log_entries_body_bytes_sent"
        ),
        sa.CheckConstraint(
            "status_code BETWEEN 100 AND 599", name="ck_log_entries_status_code"
        ),
        sa.ForeignKeyConstraint(
            ["import_id"], ["log_imports.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_log_entries_import_method",
        "log_entries",
        ["import_id", "method"],
    )
    op.create_index(
        "ix_log_entries_import_occurred",
        "log_entries",
        ["import_id", "occurred_at"],
    )
    op.create_index(
        "ix_log_entries_import_status",
        "log_entries",
        ["import_id", "status_code"],
    )


def downgrade() -> None:
    op.drop_index("ix_log_entries_import_status", table_name="log_entries")
    op.drop_index("ix_log_entries_import_occurred", table_name="log_entries")
    op.drop_index("ix_log_entries_import_method", table_name="log_entries")
    op.drop_table("log_entries")
    op.drop_table("log_imports")
