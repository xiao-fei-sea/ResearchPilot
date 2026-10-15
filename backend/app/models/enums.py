"""枚举定义，与设计文档 §5.2 各表的 ENUM 一一对应。"""
import enum


class TaskStatus(str, enum.Enum):
    """research_task.status —— 同时是流水线状态机的节点。"""

    pending = "pending"
    planning = "planning"
    searching = "searching"
    extracting = "extracting"
    synthesizing = "synthesizing"
    verifying = "verifying"
    writing = "writing"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


class SubQuestionType(str, enum.Enum):
    factual = "factual"          # 事实型
    comparative = "comparative"  # 对比型
    trend = "trend"              # 趋势型


class SourceType(str, enum.Enum):
    official_doc = "official_doc"
    github = "github"
    blog = "blog"
    news = "news"
    paper = "paper"
    forum = "forum"


class SourceStatus(str, enum.Enum):
    pending_fetch = "pending_fetch"
    fetched = "fetched"
    failed = "failed"
    irrelevant = "irrelevant"
    duplicated = "duplicated"


class ClaimVerification(str, enum.Enum):
    verified = "verified"          # ≥2 独立来源交叉验证通过
    corroborated = "corroborated"  # 有补充证据支持
    disputed = "disputed"          # 存在矛盾
    single_source = "single_source"  # 孤证
    unchecked = "unchecked"        # 未核验


class ContradictionType(str, enum.Enum):
    fact = "fact"        # 事实冲突
    caliber = "caliber"  # 口径冲突
    opinion = "opinion"  # 观点冲突


class StageName(str, enum.Enum):
    planner = "planner"
    searcher = "searcher"
    extractor = "extractor"
    synthesizer = "synthesizer"
    verifier = "verifier"
    writer = "writer"


class StageStatus(str, enum.Enum):
    running = "running"
    done = "done"
    failed = "failed"
    retrying = "retrying"


class EventLevel(str, enum.Enum):
    info = "info"
    progress = "progress"
    warn = "warn"
    error = "error"
