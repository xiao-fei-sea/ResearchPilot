"""ORM 模型统一出口：import 本模块即注册全部表到 Base.metadata。"""
from app.models.base import Base
from app.models.enums import (
    ClaimVerification,
    ContradictionType,
    EventLevel,
    SourceStatus,
    SourceType,
    StageName,
    StageStatus,
    SubQuestionType,
    TaskStatus,
)
from app.models.evidence import (
    Claim,
    ClaimEvidence,
    Contradiction,
    Document,
    Evidence,
    Source,
)
from app.models.report import Report, ReportSection
from app.models.run import EventLog, StageRun
from app.models.task import ResearchTask, SearchQuery, SubQuestion

__all__ = [
    "Base",
    "Claim",
    "ClaimEvidence",
    "ClaimVerification",
    "Contradiction",
    "ContradictionType",
    "Document",
    "EventLevel",
    "EventLog",
    "Evidence",
    "Report",
    "ReportSection",
    "ResearchTask",
    "SearchQuery",
    "Source",
    "SourceStatus",
    "SourceType",
    "StageName",
    "StageRun",
    "StageStatus",
    "SubQuestion",
    "SubQuestionType",
    "TaskStatus",
]
