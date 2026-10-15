"""报告模型：report / report_section。"""
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON, MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK, TimestampMixin

LongText = Text().with_variant(MEDIUMTEXT(), "mysql")


class Report(TimestampMixin, Base):
    """报告（带版本：regenerate 保留历史，见设计文档 §5.2 设计要点）。"""

    __tablename__ = "report"
    __table_args__ = (UniqueConstraint("task_id", "version", name="uq_report_task_version"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("research_task.id"), nullable=False, index=True
    )
    outline: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content_md: Mapped[str] = mapped_column(LongText, default="")
    # 章节树，含每章引用映射
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    # 编号 → source_id → 展示信息（标题/URL/域名/时间/可信度）
    references: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    regenerated_from: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    sections_rel: Mapped[list["ReportSection"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class ReportSection(TimestampMixin, Base):
    __tablename__ = "report_section"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("report.id"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str] = mapped_column(String(255), default="")
    content_md: Mapped[str] = mapped_column(LongText, default="")
    # {citation_no: [evidence_id, ...]}
    citation_map: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    report: Mapped[Report] = relationship(back_populates="sections_rel")
