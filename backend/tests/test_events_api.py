"""SSE 端点测试：用假 Redis 验证回放逻辑（实时通道需要真 Redis，在 Docker 冒烟中覆盖）。"""
import pytest


class FakePubSub:
    """替代 redis.PubSub：不订阅、无消息。"""

    def subscribe(self, *a, **k):
        pass

    def get_message(self, timeout=None):
        return None

    def close(self):
        pass


class FakeRedis:
    def pubsub(self, **k):
        return FakePubSub()


@pytest.fixture()
def sse_env(test_env, monkeypatch):
    monkeypatch.setattr("app.api.events.get_redis", lambda: FakeRedis())
    monkeypatch.setattr("app.api.events.MAX_STREAM_SECONDS", 3)  # 测试快速收尾
    return test_env


def _sse_lines(client, task_id, headers=None):
    with client.stream("GET", f"/api/research/{task_id}/events", headers=headers or {}) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        # 读到流自然关闭（收到 done/超时）
        lines = []
        for line in resp.iter_lines():
            lines.append(line)
            if line.startswith("event: done") or line.startswith("event: error"):
                break
    return lines


def test_sse_replays_events_and_closes_on_done(client, sse_env):
    # 先跑一个任务产生完整事件流
    task_id = client.post("/api/research", json={"topic": "SSE 回放测试"}).json()["task_id"]

    lines = _sse_lines(client, task_id)
    events = [l for l in lines if l.startswith("event: ")]
    # 回放顺序：created → stage.update ×12 → done
    assert events[0] == "event: task.created"
    assert events[-1] == "event: done"
    assert events.count("event: stage.update") == 12
    # SSE 帧携带自增 id（Last-Event-ID 游标的基础）
    ids = [int(l.split(": ")[1]) for l in lines if l.startswith("id: ")]
    assert ids == sorted(ids)


def test_sse_respects_last_event_id(client, sse_env):
    task_id = client.post("/api/research", json={"topic": "断线重连测试"}).json()["task_id"]

    # 模拟客户端收到前 3 条事件后断线（游标=3）
    lines = _sse_lines(client, task_id, headers={"Last-Event-ID": "3"})
    events = [l for l in lines if l.startswith("event: ")]
    assert len(events) < 14  # 只补发缺口
    assert events[-1] == "event: done"


def test_sse_404_for_unknown_task(client, sse_env):
    assert client.get("/api/research/999/events").status_code == 404
