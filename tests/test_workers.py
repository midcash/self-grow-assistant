"""Worker 单元测试

测试核心 Worker 的通信协议和基本逻辑。
LLM 调用使用模拟对象，不依赖外部 API。
"""

import asyncio
import pytest
from datetime import date
from unittest.mock import MagicMock, AsyncMock, patch

from backend.agent.workers.base import TaskBrief, WorkerResult, WorkerBase


# ── TaskBrief 协议测试 ──

class TestTaskBrief:
    """通信协议: Orchestrator → Worker"""

    def test_minimal_fields(self):
        b = TaskBrief(task_id="test", objective="测试任务")
        assert b.task_id == "test"
        assert b.objective == "测试任务"
        assert b.max_retries == 2
        assert b.timeout_seconds == 30

    def test_full_fields(self):
        b = TaskBrief(
            task_id="searcher",
            objective="搜索资料",
            context="用户要求查找Python教程",
            constraints=["只查本地"],
            expected_format="json",
            output_schema={"type": "object"},
            max_retries=3,
            timeout_seconds=15,
        )
        assert b.task_id == "searcher"
        assert b.constraints == ["只查本地"]
        assert b.output_schema == {"type": "object"}
        assert b.max_retries == 3
        assert b.timeout_seconds == 15


# ── WorkerResult 协议测试 ──

class TestWorkerResult:
    """通信协议: Worker → Orchestrator"""

    def test_success_result(self):
        r = WorkerResult(
            task_id="searcher",
            success=True,
            content="找到 12 位榜样",
            data={"count": 12},
            sources=["本地数据库"],
            confidence=0.85,
        )
        assert r.success is True
        assert r.content == "找到 12 位榜样"
        assert r.data == {"count": 12}
        assert r.sources == ["本地数据库"]
        assert r.confidence == 0.85

    def test_failure_result(self):
        r = WorkerResult(
            task_id="profiler",
            success=False,
            content="数据库连接失败",
            confidence=0.0,
        )
        assert r.success is False
        assert r.confidence == 0.0


# ── WorkerBase retry/timeout 测试 ──

class TestWorkerRetry:
    """execute_with_retry: 超时 + 重试"""

    def test_retry_on_failure(self):
        """失败时自动重试 max_retries 次"""

        class FailingWorker(ConcreteWorker):
            async def execute(self, brief):
                return WorkerResult(task_id=brief.task_id, success=False, content="fail")

        worker = FailingWorker()
        result = asyncio.run(worker.execute_with_retry(
            TaskBrief(task_id="t", objective="x", max_retries=2)
        ))
        assert result.success is False
        assert "重试 2 次" in result.content

    def test_timeout_triggers_retry(self):
        """超时后触发重试"""

        class SlowWorker(ConcreteWorker):
            async def execute(self, brief):
                await asyncio.sleep(5)
                return WorkerResult(task_id="t", success=True, content="ok")

        worker = SlowWorker()
        result = asyncio.run(worker.execute_with_retry(
            TaskBrief(task_id="t", objective="x", max_retries=1, timeout_seconds=0.1)
        ))
        assert result.success is False
        assert "重试 1 次" in result.content

    def test_success_no_retry(self):
        """成功时不做多余重试"""

        class GoodWorker(ConcreteWorker):
            async def execute(self, brief):
                return WorkerResult(task_id="t", success=True, content="ok")

        worker = GoodWorker()
        result = asyncio.run(worker.execute_with_retry(
            TaskBrief(task_id="t", objective="x")
        ))
        assert result.success is True
        assert result.content == "ok"


class ConcreteWorker(WorkerBase):
    """测试用的最小 Worker 实现"""
    @property
    def role(self): return "test"
    @property
    def system_prompt(self): return ""

    async def execute(self, brief: TaskBrief) -> WorkerResult:
        return WorkerResult(task_id=brief.task_id, success=True, content="ok")


# ── Searcher MCP 决策测试 ──

class TestSearcherMcpDecision:
    """Searcher 的 MCP 按需调用决策"""

    def test_no_mcp_when_no_config(self):
        from backend.agent.workers.searcher import SearcherWorker
        SearcherWorker._mcp_config = None
        w = SearcherWorker()
        assert w._needs_mcp(TaskBrief(task_id="s", objective="查资料"), 0) is False

    def test_trigger_mcp_when_local_insufficient(self):
        from backend.agent.workers.searcher import SearcherWorker
        SearcherWorker._mcp_config = {"command": "python", "args": ["test.py"]}
        w = SearcherWorker()
        assert w._needs_mcp(TaskBrief(task_id="s", objective="查资料"), 1) is True

    def test_trigger_mcp_by_keyword(self):
        from backend.agent.workers.searcher import SearcherWorker
        SearcherWorker._mcp_config = {"command": "python", "args": ["test.py"]}
        w = SearcherWorker()
        assert w._needs_mcp(
            TaskBrief(task_id="s", objective="搜索知识库中的文档"),
            10  # 本地结果足够但关键词匹配
        ) is True

    def test_skip_mcp_when_local_sufficient(self):
        from backend.agent.workers.searcher import SearcherWorker
        SearcherWorker._mcp_config = {"command": "python", "args": ["test.py"]}
        w = SearcherWorker()
        assert w._needs_mcp(TaskBrief(task_id="s", objective="查一下"), 5) is False


# ── MotivationEngine 压力计算测试 ──

class TestMotivationPressure:
    """MotivationEngine 压力计算算法"""

    def test_pressure_near_deadline_low_progress(self):
        from backend.agent.motivation_engine import MotivationEngine
        engine = MotivationEngine()

        goal = MagicMock()
        goal.target_metric = "1"  # Would fail - test parse robustness
        goal.current_progress = 0
        goal.importance = 9
        goal.deadline = date(2026, 5, 25)

        with patch.object(engine, '_calc_pressure', wraps=engine._calc_pressure) as m:
            p = engine._calc_pressure(goal, date(2026, 5, 23))
            # 2 days left, 0 progress, importance 9 → expect high pressure
            assert p > 0

    def test_pressure_parse_numeric_metric(self):
        from backend.agent.motivation_engine import MotivationEngine
        engine = MotivationEngine()

        goal = MagicMock()
        goal.target_metric = "10"
        goal.current_progress = 1
        goal.importance = 9
        goal.deadline = date(2026, 5, 25)

        p = engine._calc_pressure(goal, date(2026, 5, 23))
        assert p > 0

    def test_pressure_parse_string_metric(self):
        from backend.agent.motivation_engine import MotivationEngine
        engine = MotivationEngine()

        goal = MagicMock()
        goal.target_metric = "投10份简历"
        goal.current_progress = 1
        goal.importance = 9
        goal.deadline = date(2026, 5, 25)

        p = engine._calc_pressure(goal, date(2026, 5, 23))
        assert p > 0


# ── Goal CRUD 集成测试 ──

class TestGoalCrud:
    """Goal CRUD API 集成测试"""

    @pytest.fixture
    def client(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_create_and_list_goals(self, client):
        r = client.post("/api/v1/agent/goals", json={
            "title": "测试目标", "deadline": "2026-12-31",
            "target_metric": "5", "importance": 5,
        })
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["title"] == "测试目标"

        r = client.get("/api/v1/agent/goals")
        assert r.status_code == 200
        goals = r.json()["data"]
        assert len(goals) >= 1
