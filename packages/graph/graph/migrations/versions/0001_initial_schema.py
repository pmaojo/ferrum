"""Initial schema from SQL files."""

from __future__ import annotations

from pathlib import Path

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql_dir = Path(__file__).resolve().parents[2] / "database" / "schema"
    for name in ["knowledge_graphs.sql", "repository_ingestions.sql"]:
        with open(sql_dir / name, "r", encoding="utf-8") as f:
            op.execute(f.read())


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS repository_ingestions CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS update_repository_ingestions_updated_at() CASCADE;")
    op.execute("DROP TABLE IF EXISTS knowledge_graphs CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS update_knowledge_graphs_updated_at() CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS knowledge_graph_stats CASCADE;")
    op.execute("DROP VIEW IF EXISTS public_knowledge_graphs CASCADE;")
