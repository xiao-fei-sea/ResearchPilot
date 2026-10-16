"""API 层测试：创建任务（含 eager 流水线）、查询、取消。"""
from app.db import session_scope
from app.models import TaskStatus


def test_create_task_runs_pipeline_and_reaches_done(client):
    resp = client.post("/api/research", json={"topic": "调研 2025–2026 年 AI Agent"})
    assert resp.status_code == 202
    body = resp.json()
    task_id = body["task_id"]

    # eager 流水线已在请求内执行完毕
    detail = client.get(f"/api/research/{task_id}").json()
    assert detail["status"] == "done"
    assert detail["budget"]["max_sources"] == 60
    assert detail["stats"]["sub_questions"] == 5


def test_list_tasks(client):
    client.post("/api/research", json={"topic": "主题一"})
    client.post("/api/research", json={"topic": "主题二"})
    data = client.get("/api/research").json()
    assert data["total"] == 2
    assert [i["topic"] for i in data["items"]] == ["主题二", "主题一"]  # 倒序


def test_get_task_404(client):
    assert client.get("/api/research/999").status_code == 404


def test_topic_validation(client):
    assert client.post("/api/research", json={"topic": "x"}).status_code == 422


def test_cancel(client):
    task_id = client.post("/api/research", json={"topic": "可取消的主题"}).json()["task_id"]
    # eager 流水线已完成，取消接口应对终态任务幂等返回
    resp = client.post(f"/api/research/{task_id}/cancel").json()
    assert resp["status"] in ("done", "cancelled")


def test_cancel_running_task(client, monkeypatch):
    """让流水线卡住以测试取消：置为 planning 后调用 cancel。"""
    from app.models import ResearchTask

    task_id = client.post("/api/research", json={"topic": "主题"}).json()["task_id"]
    with session_scope() as db:
        # 人为回到非终态，模拟运行中
        db.get(ResearchTask, task_id).status = TaskStatus.planning
    resp = client.post(f"/api/research/{task_id}/cancel").json()
    assert resp["status"] == "cancelled"
