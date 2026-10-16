"""P0 冒烟流水线：模拟六阶段跑通 API → Celery → MySQL → Redis → SSE 全链路。

结构要点：每个阶段一个独立事务（session_scope）——
- 阶段进度即时可见（前端轮询/SSE 都能拿到）；
- 取消检查读取的是最新已提交状态（大事务内 refresh 会丢未提交修改）；
- M1 真实流水线沿用同样的阶段边界约定。
"""
import logging
import time

from app.celery import celery_app
from app.db import session_scope
from app.events import emit_event
from app.models import ResearchTask, StageName, StageRun, StageStatus, SubQuestion, TaskStatus

logger = logging.getLogger("app.tasks.smoke")

# task.status ↔ 阶段的映射（设计文档 §5.2 research_task.status）
STAGE_TASK_STATUS = {
    StageName.planner: TaskStatus.planning,
    StageName.searcher: TaskStatus.searching,
    StageName.extractor: TaskStatus.extracting,
    StageName.synthesizer: TaskStatus.synthesizing,
    StageName.verifier: TaskStatus.verifying,
    StageName.writer: TaskStatus.writing,
}

# 模拟的子问题拆解结果（示例主题，来自设计文档 §2）
MOCK_SUB_QUESTIONS = [
    "2025–2026 年 AI Agent 在软件工程领域有哪些代表性应用形态？",
    "主流开源项目（OpenHands、SWE-agent、Aider 等）各自的架构是什么？",
    "这些项目在基准测试（SWE-bench 等）上的表现与优缺点对比？",
    "各项目背后的团队/公司、商业模式与发展路线？",
    "该领域公认的发展趋势与争议点是什么？",
]

STAGE_SUMMARIES = {
    StageName.planner: {"sub_questions": len(MOCK_SUB_QUESTIONS), "queries": 10},
    StageName.searcher: {"sources_found": 42, "sources_selected": 60},
    StageName.extractor: {"fetched": 51, "failed": 3, "evidence": 137},
    StageName.synthesizer: {"claims": 46, "contradictions": 3},
    StageName.verifier: {"verified": 28, "single_source": 5},
    StageName.writer: {"sections": 7, "citations": 112},
}


def _begin_stage(db, task_id: int, stage: StageName) -> StageRun:
    """标记任务进入阶段，创建 stage_run，发 running 事件。"""
    task = db.get(ResearchTask, task_id)
    run = StageRun(task_id=task_id, stage=stage, status=StageStatus.running)
    db.add(run)
    task.status = STAGE_TASK_STATUS[stage]
    emit_event(
        db, task_id, "stage.update",
        {"stage": stage.value, "status": "running", "message": f"{stage.value} 阶段开始"},
        stage_run_id=run.id,
    )
    return run


def _finish_stage(db, task_id: int, run: StageRun, cancelled: bool) -> None:
    """阶段收尾：写模拟产物、合并统计、发 done 事件。"""
    stage = run.stage
    run.status = StageStatus.done
    if stage == StageName.planner:
        for seq, content in enumerate(MOCK_SUB_QUESTIONS, start=1):
            db.add(SubQuestion(task_id=task_id, seq=seq, content=content, round=1))
    summary = STAGE_SUMMARIES[stage]
    emit_event(
        db, task_id, "stage.update",
        {"stage": stage.value, "status": "done",
         "message": f"{stage.value} 阶段完成", "summary": summary},
        stage_run_id=run.id,
    )
    # 统计合并进 task.stats（本阶段事务内读改写，无 refresh 丢改问题）
    task = db.get(ResearchTask, task_id)
    task.stats = {**(task.stats or {}), **summary}


@celery_app.task(name="app.tasks.smoke.run_smoke_pipeline", bind=True, max_retries=0)
def run_smoke_pipeline(self, task_id: int) -> dict:
    logger.info("smoke pipeline start", extra={"task_id": task_id})
    stats: dict = {}

    for stage in StageName:
        # 1) 进入阶段（独立事务，阶段边界即取消检查点，见设计文档 §7.3）
        with session_scope() as db:
            task = db.get(ResearchTask, task_id)
            if task is None:
                logger.error("task not found", extra={"task_id": task_id})
                return {"ok": False}
            if task.status == TaskStatus.cancelled:
                logger.info("smoke pipeline cancelled", extra={"task_id": task_id})
                return {"ok": False, "cancelled": True}
            run = _begin_stage(db, task_id, stage)
            run_id = run.id

        time.sleep(1.0)  # 模拟阶段耗时（不占数据库事务）

        # 2) 阶段收尾（再次开事务；中途被取消则保留 running 记录直接退出）
        with session_scope() as db:
            task = db.get(ResearchTask, task_id)
            if task.status == TaskStatus.cancelled:
                logger.info("smoke pipeline cancelled mid-stage", extra={"task_id": task_id})
                return {"ok": False, "cancelled": True}
            run = db.get(StageRun, run_id)
            _finish_stage(db, task_id, run, cancelled=False)
            stats.update(STAGE_SUMMARIES[stage])

    # 3) 收官
    with session_scope() as db:
        task = db.get(ResearchTask, task_id)
        task.status = TaskStatus.done
        emit_event(db, task_id, "done", {"message": "研究任务完成（P0 模拟）"})
    logger.info("smoke pipeline done", extra={"task_id": task_id})
    return {"ok": True}
