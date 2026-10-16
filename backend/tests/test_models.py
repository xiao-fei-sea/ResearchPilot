"""数据模型冒烟：建表 + 插入回环 + 唯一约束。"""
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.db import session_scope
from app.models import (
    Claim,
    ClaimEvidence,
    Contradiction,
    Evidence,
    ResearchTask,
    Source,
    SubQuestion,
    TaskStatus,
)


def test_task_and_relations_roundtrip(test_env):
    with session_scope() as db:
        task = ResearchTask(topic="调研 AI Agent", status=TaskStatus.pending)
        db.add(task)
        db.flush()
        db.add(SubQuestion(task_id=task.id, seq=1, content="有哪些应用形态？", round=1))
        source = Source(task_id=task.id, url="https://example.com/a", url_hash="h" * 64)
        db.add(source)
        db.flush()
        db.add(
            Evidence(
                source_id=source.id,
                sub_question_id=1,
                quote="原文摘录",
                relevance=Decimal("0.90"),
            )
        )

    with session_scope() as db:
        loaded = db.get(ResearchTask, task.id)
        assert loaded.status == TaskStatus.pending
        assert loaded.sub_questions[0].content == "有哪些应用形态？"
        assert loaded.sub_questions[0].task.topic == "调研 AI Agent"
        assert str(loaded.status.value) == "pending"


def test_url_hash_unique(test_env):
    with pytest.raises(IntegrityError):
        with session_scope() as db:
            task = ResearchTask(topic="t1")
            db.add(task)
            db.flush()
            db.add(Source(task_id=task.id, url="https://a.com", url_hash="x" * 64))
            db.add(Source(task_id=task.id, url="https://b.com", url_hash="x" * 64))
            db.flush()  # 唯一约束在 flush 时触发；session_scope 负责回滚


def test_claim_with_evidence_and_contradiction(test_env):
    with session_scope() as db:
        task = ResearchTask(topic="t2")
        db.add(task)
        db.flush()
        s1 = Source(task_id=task.id, url="https://a.com", url_hash="a" * 64)
        s2 = Source(task_id=task.id, url="https://b.com", url_hash="b" * 64)
        db.add_all([s1, s2])
        db.flush()
        e1 = Evidence(source_id=s1.id, sub_question_id=1, quote="q1")
        e2 = Evidence(source_id=s2.id, sub_question_id=1, quote="q2")
        db.add_all([e1, e2])
        db.flush()
        c1 = Claim(task_id=task.id, text="论断 A")
        c2 = Claim(task_id=task.id, text="论断 B")
        db.add_all([c1, c2])
        db.flush()
        db.add(ClaimEvidence(claim_id=c1.id, evidence_id=e1.id))
        db.add(
            Contradiction(
                task_id=task.id,
                type="fact",
                description="双方数据冲突",
                claim_a_id=c1.id,
                claim_b_id=c2.id,
            )
        )

    with session_scope() as db:
        assert db.query(ClaimEvidence).count() == 1
        assert db.query(Contradiction).one().type == "fact"
