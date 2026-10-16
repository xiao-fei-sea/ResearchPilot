"""证据侧模型：source / document / evidence / claim / contradiction。"""
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import JSON, MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK, TimestampMixin
from app.models.enums import ClaimVerification, ContradictionType, SourceStatus, SourceType

# MySQL 用 MEDIUMTEXT 存长正文，其他方言退化为 TEXT
LongText = Text().with_variant(MEDIUMTEXT(), "mysql")


class Source(TimestampMixin, Base):
    """搜索结果条目（设计文档 §5.2 source）。"""

    __tablename__ = "source"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("research_task.id"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    # 归一化 URL 的 SHA-256，抓取幂等的关键（设计文档 §5.2 设计要点）
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    source_type: Mapped[SourceType | None] = mapped_column(nullable=True)
    domain: Mapped[str] = mapped_column(String(255), default="", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[SourceStatus] = mapped_column(
        default=SourceStatus.pending_fetch, nullable=False, index=True
    )
    credibility: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    # jina/playwright/direct
    fetch_channel: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    content_simhash: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    document: Mapped["Document | None"] = relationship(  # noqa: F821
        back_populates="source", uselist=False, cascade="all, delete-orphan"
    )
    evidence: Mapped[list["Evidence"]] = relationship(  # noqa: F821
        back_populates="source", cascade="all, delete-orphan"
    )


class Document(Base):
    """抓取到的正文快照。"""

    __tablename__ = "document"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("source.id"), nullable=False, unique=True
    )
    content: Mapped[str] = mapped_column(LongText, default="")
    content_md: Mapped[str] = mapped_column(LongText, default="")
    char_count: Mapped[int] = mapped_column(default=0, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    source: Mapped[Source] = relationship(back_populates="document")


class Evidence(Base):
    """可回溯的最小证据单元（逐字摘录 ≤200 字）。"""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("source.id"), nullable=False, index=True
    )
    sub_question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sub_question.id"), nullable=False, index=True
    )
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    # 页内定位：段落索引 / 标题路径，保证点开能找到原文位置
    anchor: Mapped[str] = mapped_column(String(255), default="")
    relevance: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)

    source: Mapped[Source] = relationship(back_populates="evidence")


class Claim(TimestampMixin, Base):
    """论断：综合阶段归纳出的写作原子素材。"""

    __tablename__ = "claim"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("research_task.id"), nullable=False, index=True
    )
    sub_question_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sub_question.id"), nullable=True, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    topic_tag: Mapped[str] = mapped_column(String(128), default="")
    verification: Mapped[ClaimVerification] = mapped_column(
        default=ClaimVerification.unchecked, nullable=False
    )


class ClaimEvidence(Base):
    """论断-证据挂接（多对多，复合主键）。"""

    __tablename__ = "claim_evidence"

    claim_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("claim.id"), primary_key=True
    )
    evidence_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("evidence.id"), primary_key=True
    )


class Contradiction(TimestampMixin, Base):
    """矛盾记录：两个论断之间的冲突。"""

    __tablename__ = "contradiction"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("research_task.id"), nullable=False, index=True
    )
    type: Mapped[ContradictionType] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    claim_a_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("claim.id"), nullable=False
    )
    claim_b_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("claim.id"), nullable=False
    )
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)  # verifier 的裁决建议


# 按任务拉取待抓取来源
Index("ix_source_task_status", Source.task_id, Source.status)
