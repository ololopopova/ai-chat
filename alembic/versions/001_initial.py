"""Initial migration - create all tables.

Revision ID: 001
Revises:
Create Date: 2024-12-23

Creates:
- Extensions: vector, pg_trgm
- Enum: job_status
- Tables: domains, chunks, conversations, jobs
- Indexes: GIN for FTS, HNSW for vector search
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade database schema."""
    # ==========================================
    # Расширения PostgreSQL
    # ==========================================
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ==========================================
    # ENUM для статуса задачи
    # ==========================================
    job_status = postgresql.ENUM(
        "queued",
        "running",
        "completed",
        "failed",
        "cancelled",
        name="job_status",
        create_type=False,
    )
    job_status.create(op.get_bind(), checkfirst=True)

    # ==========================================
    # Таблица domains
    # ==========================================
    op.create_table(
        "domains",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False, comment="Название домена"),
        sa.Column(
            "slug",
            sa.String(length=50),
            nullable=False,
            comment="URL-friendly идентификатор",
        ),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание домена"),
        sa.Column("google_doc_url", sa.Text(), nullable=False, comment="Ссылка на Google Doc"),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Активен ли домен",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_domains")),
        sa.UniqueConstraint("slug", name=op.f("uq_domains_slug")),
    )
    op.create_index(op.f("ix_domains_is_active"), "domains", ["is_active"], unique=False)
    op.create_index(op.f("ix_domains_slug"), "domains", ["slug"], unique=True)

    # ==========================================
    # Таблица chunks
    # ==========================================
    op.create_table(
        "chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("domain_id", sa.UUID(), nullable=False, comment="ID домена"),
        sa.Column("content", sa.Text(), nullable=False, comment="Текст фрагмента"),
        sa.Column(
            "content_tsv",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('russian', content) || to_tsvector('english', content)",
                persisted=True,
            ),
            nullable=False,
            comment="Полнотекстовый индекс",
        ),
        sa.Column(
            "embedding",
            Vector(1536),
            nullable=True,
            comment="Векторное представление",
        ),
        sa.Column(
            "chunk_index",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Порядковый номер в документе",
        ),
        sa.Column(
            "chunk_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Дополнительные данные",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["domain_id"],
            ["domains.id"],
            name=op.f("fk_chunks_domain_id_domains"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chunks")),
    )
    op.create_index(op.f("ix_chunks_domain_id"), "chunks", ["domain_id"], unique=False)
    op.create_index(
        "ix_chunks_domain_id_chunk_index",
        "chunks",
        ["domain_id", "chunk_index"],
        unique=False,
    )

    # GIN индекс для полнотекстового поиска
    op.create_index(
        "ix_chunks_content_tsv",
        "chunks",
        ["content_tsv"],
        unique=False,
        postgresql_using="gin",
    )

    # HNSW индекс для векторного поиска (cosine distance)
    op.execute(
        """
        CREATE INDEX ix_chunks_embedding
        ON chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )

    # ==========================================
    # Таблица conversations
    # ==========================================
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "thread_id",
            sa.String(length=100),
            nullable=False,
            comment="Внешний идентификатор thread",
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=True,
            comment="Заголовок диалога",
        ),
        sa.Column(
            "messages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="История сообщений",
        ),
        sa.Column(
            "state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Состояние LangGraph",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
        sa.UniqueConstraint("thread_id", name=op.f("uq_conversations_thread_id")),
    )
    op.create_index(
        op.f("ix_conversations_created_at"),
        "conversations",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversations_thread_id"),
        "conversations",
        ["thread_id"],
        unique=True,
    )

    # ==========================================
    # Таблица jobs
    # ==========================================
    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "thread_id",
            sa.String(length=100),
            nullable=True,
            comment="ID связанного диалога",
        ),
        sa.Column(
            "tool_name",
            sa.String(length=100),
            nullable=False,
            comment="Название инструмента",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "queued",
                "running",
                "completed",
                "failed",
                "cancelled",
                name="job_status",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'queued'"),
            comment="Статус задачи",
        ),
        sa.Column(
            "progress",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Прогресс 0-100",
        ),
        sa.Column(
            "current_step",
            sa.String(length=255),
            nullable=True,
            comment="Текущий шаг выполнения",
        ),
        sa.Column(
            "input_params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Входные параметры",
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Результат выполнения",
        ),
        sa.Column("error", sa.Text(), nullable=True, comment="Текст ошибки"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Время начала",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Время завершения",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index(op.f("ix_jobs_created_at"), "jobs", ["created_at"], unique=False)
    op.create_index(
        "ix_jobs_status_created_at",
        "jobs",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_jobs_thread_id"), "jobs", ["thread_id"], unique=False)
    op.create_index(op.f("ix_jobs_tool_name"), "jobs", ["tool_name"], unique=False)
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    # Удаляем таблицы в обратном порядке
    op.drop_table("jobs")
    op.drop_table("conversations")
    op.drop_table("chunks")
    op.drop_table("domains")

    # Удаляем ENUM
    op.execute("DROP TYPE IF EXISTS job_status")

    # Расширения обычно не удаляем
    # op.execute("DROP EXTENSION IF EXISTS vector")
    # op.execute("DROP EXTENSION IF EXISTS pg_trgm")
