"""任务侧模型：research_task / sub_question / search_query。"""
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK, TimestampMixin
from app.models.enums import SubQuestionType, TaskStatus


class ResearchTask(TimestampMixin, Base):
    __tablename__ = "research_task"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        default=TaskStatus.pending, nullable=False, index=True
    )
    # 用户参数：深度/语言/时间范围/篇幅/模型覆盖
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # 预算：max_sources/max_rounds/token/时长
    budget: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # 运行统计：来源数/证据数/耗时/token 消耗
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    sub_questions: Mapped[list["SubQuestion"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    stage_runs: Mapped[list["StageRun"]] = relationship(  # noqa: F821
        back_populates="task", cascade="all, delete-orphan"
    )


class SubQuestion(Base):
    __tablename__ = "sub_question"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("research_task.id"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[SubQuestionType] = mapped_column(default=SubQuestionType.factual
    )
    # open / gap_found / closed（synthesizer 维护）
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    # 完成判据与信息缺口（planner 写判据，synthesizer 写 gaps）
    coverage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # 第几轮检索产生（初始为 1，gap 循环补建的子问题 >1）
    round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    task: Mapped[ResearchTask] = relationship(back_populates="sub_questions")
    queries: Mapped[list["SearchQuery"]] = relationship(
        back_populates="sub_question", cascade="all, delete-orphan"
    )


class SearchQuery(TimestampMixin, Base):
    __tablename__ = "search_query"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    sub_question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sub_question.id"), nullable=False, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str] = mapped_column(CHAR(2), default="zh", nullable=False)
    engine: Mapped[str] = mapped_column(String(32), default="tavily", nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    sub_question: Mapped[SubQuestion] = relationship(back_populates="queries")


# 高频查询：按任务取子问题并排序
Index("ix_sub_question_task_seq", SubQuestion.task_id, SubQuestion.seq)
# 防重复登记同一查询（同一子问题同一轮不重复）
UniqueConstraint("sub_question_id", "round", "query", name="uq_query_once")
