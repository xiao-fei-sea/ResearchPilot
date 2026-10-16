"""冒烟流水线测试：eager 模式直跑 Celery 任务，验证 DB 终态与事件流。"""
from app.db import session_scope
from app.models import EventLog, ResearchTask, StageRun, SubQuestion, TaskStatus
from app.tasks.smoke import run_smoke_pipeline


def _make_task() -> int:
    with session_scope() as db:
        task = ResearchTask(topic="调研 2025–2026 年 AI Agent 在软件工程中的应用")
        db.add(task)
        db.flush()
        return task.id


def test_pipeline_reaches_done(test_env):
    task_id = _make_task()
    result = run_smoke_pipeline.apply(args=[task_id]).get()
    assert result == {"ok": True}

    with session_scope() as db:
        task = db.get(ResearchTask, task_id)
        assert task.status == TaskStatus.done
        assert db.query(SubQuestion).filter_by(task_id=task_id).count() == 5
        assert db.query(StageRun).filter_by(task_id=task_id).count() == 6
        assert db.query(StageRun).filter_by(task_id=task_id, status="done").count() == 6
        # 事件流完整：直跑任务没有 task.created（那是 API 发的），每阶段 2 条 + done
        types = [e.type for e in db.query(EventLog).filter_by(task_id=task_id)]
        assert types[0] == "stage.update"
        assert types[-1] == "done"
        assert types.count("stage.update") == 12
        # 统计信息合并进 task.stats
        assert task.stats["evidence"] == 137


def test_pipeline_honours_cancel(test_env):
    task_id = _make_task()
    with session_scope() as db:
        db.get(ResearchTask, task_id).status = TaskStatus.cancelled

    result = run_smoke_pipeline.apply(args=[task_id]).get()
    assert result == {"ok": False, "cancelled": True}
    with session_scope() as db:
        assert db.get(ResearchTask, task_id).status == TaskStatus.cancelled
