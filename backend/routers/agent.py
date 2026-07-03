"""智能体 API 路由

端点:
- GET  /api/v1/agent/status          智能体状态
- POST /api/v1/agent/chat            对话
- POST /api/v1/agent/chat/stream     流式对话 (SSE)
- POST /api/v1/agent/evaluate        手动触发优先级评估
- GET  /api/v1/agent/tasks/priority  优先级排序后的任务
- POST /api/v1/agent/tts             文字转语音
- GET  /api/v1/agent/schedule/status 调度器状态
- POST /api/v1/agent/schedule/toggle 开关定时评估
- PUT  /api/v1/agent/schedule/cron   修改 cron 表达式
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.models import TodoItem, AgentConversation, AgentTaskPriority
from backend.agent.harness import AgentHarness

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

# 全局 Harness 实例 (由 main.py 在启动时初始化)
_harness: AgentHarness | None = None


def get_harness() -> AgentHarness:
    if _harness is None:
        raise HTTPException(503, "Agent not initialized")
    return _harness


def set_harness(harness: AgentHarness) -> None:
    global _harness
    _harness = harness


# === 统一响应包装 ===

def ok(data=None):
    """包装为前端期望的 {code, message, data} 格式"""
    return {"code": 0, "message": "success", "data": data}


async def _try_tts_with_fallback(harness, tts, req):
    """尝试 TTS，失败时自动降级到 fallback 引擎"""
    # 1. 尝试默认引擎
    try:
        return await tts.synthesize(req.text, voice=req.voice, speed=req.speed)
    except Exception as e:
        logger.warning(f"Primary TTS failed: {e}")

    # 2. 尝试 fallback 引擎
    fallback_name = harness._config.get("plugins", {}).get("tts", {}).get("fallback", "")
    if fallback_name and fallback_name != harness._config.get("plugins", {}).get("tts", {}).get("default", ""):
        try:
            from backend.agent.plugins.tts_engine.factory import TTSFactory
            fb_cfg = harness._config.get("plugins", {}).get("tts", {}).get(fallback_name, {})
            fb_engine = TTSFactory.create(fallback_name)
            await fb_engine.on_load(fb_cfg)
            logger.info(f"TTS fallback to {fallback_name}")
            return await fb_engine.synthesize(req.text, voice=req.voice, speed=req.speed)
        except Exception as e2:
            logger.error(f"Fallback TTS also failed: {e2}")

    return None


# === 请求模型 ===

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)


class TTSRequest(BaseModel):
    text: str
    voice: str | None = None
    speed: float = 1.0


class CronUpdateRequest(BaseModel):
    cron: str = "*/20 * * * *"


# === 状态 ===

@router.get("/status")
async def agent_status():
    if _harness is None:
        return ok({"initialized": False, "message": "Agent not started"})
    health = await _harness.health_check()
    health["config"] = {
        "llm_provider": _harness._config.get("plugins", {}).get("llm", {}).get("default", "deepseek"),
        "tts_provider": _harness._config.get("plugins", {}).get("tts", {}).get("default", "qwen"),
        "cron": _harness._config.get("agent", {}).get("cron", "*/20 * * * *"),
        "live2d_enabled": _harness._config.get("live2d", {}).get("enabled", False),
    }
    # MCP 连接状态
    mcp_cfg = _harness._config.get("mcp_servers", [])
    health["config"]["mcp_active"] = len(mcp_cfg) > 0
    health["mcp"] = {
        "servers": len(mcp_cfg),
        "active": [{"name": m.get("name"), "transport": m.get("transport", "stdio")} for m in mcp_cfg],
    }
    return ok(health)


@router.get("/activity")
async def agent_activity(limit: int = 10):
    """Agent 活动日志：最近编排记录，含 Worker 调用链路"""
    from pathlib import Path
    import re

    log_dir = Path("data/agent-memory/plan-logs")
    if not log_dir.exists():
        return ok([])

    logs = sorted(log_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    result = []
    for f in logs:
        content = f.read_text(encoding="utf-8")
        info = {"file": f.name, "time": f.name[:19].replace("-", ":"), "workers": []}

        # 解析 Worker 执行表格
        in_table = False
        for line in content.split("\n"):
            line = line.strip()
            if "用户消息" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                info["message"] = parts[-1][:100] if len(parts) >= 2 else ""
            if "总耗时" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                info["elapsed"] = parts[-1] if len(parts) >= 2 else ""
            # Worker 表格行: | searcher | 目标描述 | 耗时ms | OK/FAIL |
            if line.startswith("|") and not line.startswith("| Worker") and not line.startswith("|---"):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 4 and any(parts[0] in w for w in ["searcher", "profiler", "executor", "goal_decomposer", "coach"]):
                    info["workers"].append({
                        "name": parts[0],
                        "objective": parts[1][:60] if len(parts) > 1 else "",
                        "elapsed": parts[2] if len(parts) > 2 else "",
                        "result": parts[3] if len(parts) > 3 else "",
                    })

        # Fallback: 从 JSON 中提取
        if not info["workers"]:
            json_start = content.find('"subtasks"')
            if json_start != -1:
                snippet = content[json_start:json_start+2000]
                for m in re.finditer(r'"id":\s*"(\w+)"', snippet):
                    name = m.group(1)
                    info["workers"].append({"name": name, "objective": "", "elapsed": "", "result": ""})

        result.append(info)
    return ok(result)


@router.get("/knowledge")
async def agent_knowledge():
    """MCP 工具列表 + 知识库文档"""
    try:
        from backend.agent.workers.searcher import SearcherWorker
        if not SearcherWorker._mcp_config:
            return ok({"connected": False, "message": "MCP 未配置"})

        import asyncio
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        cfg = SearcherWorker._mcp_config
        params = StdioServerParameters(command=cfg["command"], args=cfg.get("args", []))
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()

                # 获取 MCP 工具列表
                tools_resp = await asyncio.wait_for(s.list_tools(), timeout=15)
                tools_list = getattr(tools_resp, "tools", tools_resp)
                tools = []
                for t in (tools_list if isinstance(tools_list, list) else []):
                    name = getattr(t, "name", str(t))
                    desc = getattr(t, "description", "")
                    tools.append({"name": name, "description": desc[:120] if desc else ""})

                # 获取文集列表
                result = await asyncio.wait_for(
                    s.call_tool("list_collections", {"include_stats": True}),
                    timeout=15,
                )
                collections_text = ""
                for b in getattr(result, "content", []):
                    if hasattr(b, "text"):
                        collections_text += b.text

                return ok({
                    "connected": True,
                    "server": cfg.get("name", "MCP Server"),
                    "tools": tools,
                    "collections": collections_text,
                })
    except Exception as e:
        return ok({"connected": False, "message": str(e)[:200]})


# === Agent 可观测性 (Trace + Metrics) ===

@router.get("/traces")
async def agent_traces(
    limit: int = 20,
    agent_name: str = "",
    date: str = "",
    success: str = "",
):
    """编排 Trace 列表"""
    try:
        from backend.database import SessionLocal
        from backend.models import AgentTrace
        from datetime import date as date_type, timedelta

        db = SessionLocal()
        try:
            q = db.query(AgentTrace)

            if agent_name:
                q = q.filter(AgentTrace.agent_name == agent_name)
            if date:
                d = date_type.fromisoformat(date)
                q = q.filter(AgentTrace.created_at >= d, AgentTrace.created_at < d + timedelta(days=1))
            if success == "true":
                q = q.filter(AgentTrace.success == True)
            elif success == "false":
                q = q.filter(AgentTrace.success == False)

            # 按 orchestration_id 分组，取每组最新的 span 作为摘要
            spans = q.order_by(AgentTrace.created_at.desc()).limit(limit * 20).all()

            # 按 orchestration_id 去重聚合
            orch_map: dict[str, dict] = {}
            for s in spans:
                oid = s.orchestration_id
                if oid not in orch_map:
                    orch_map[oid] = {
                        "orchestration_id": oid,
                        "intent": s.objective if s.span_type == "plan" else "",
                        "workers_used": [],
                        "total_latency_ms": 0,
                        "success": True,
                        "created_at": s.created_at.isoformat() if s.created_at else "",
                        "reply_preview": "",
                    }
                if s.span_type == "plan":
                    orch_map[oid]["intent"] = s.objective
                elif s.span_type == "worker_execute":
                    if s.agent_name not in orch_map[oid]["workers_used"]:
                        orch_map[oid]["workers_used"].append(s.agent_name)
                    orch_map[oid]["total_latency_ms"] += s.latency_ms
                elif s.span_type == "synthesis":
                    orch_map[oid]["reply_preview"] = s.output_summary[:80]
                if not s.success:
                    orch_map[oid]["success"] = False

            result = sorted(orch_map.values(), key=lambda x: x["created_at"], reverse=True)[:limit]
            return ok(result)
        finally:
            db.close()
    except Exception as e:
        return ok([])


@router.get("/traces/{orchestration_id}")
async def agent_trace_detail(orchestration_id: str):
    """编排 Trace 完整 span 树"""
    try:
        from backend.database import SessionLocal
        from backend.models import AgentTrace

        db = SessionLocal()
        try:
            spans = db.query(AgentTrace).filter(
                AgentTrace.orchestration_id == orchestration_id
            ).order_by(AgentTrace.id).all()

            return ok([{
                "id": str(s.id),
                "orchestration_id": s.orchestration_id,
                "span_type": s.span_type,
                "agent_name": s.agent_name,
                "parent_span_id": str(s.parent_span_id) if s.parent_span_id else None,
                "objective": s.objective,
                "input_summary": s.input_summary,
                "output_summary": s.output_summary,
                "latency_ms": s.latency_ms,
                "success": s.success,
                "error_message": s.error_message,
                "metadata_json": s.metadata_json,
                "created_at": s.created_at.isoformat() if s.created_at else "",
            } for s in spans])
        finally:
            db.close()
    except Exception as e:
        return ok([])


@router.get("/metrics")
async def agent_metrics(days: int = 7, agent_name: str = ""):
    """Agent 指标聚合"""
    try:
        from backend.agent.observability.metrics import MetricsAggregator
        agg = MetricsAggregator()
        data = agg.get_metrics(days=days, agent_name=agent_name if agent_name else None)
        return ok(data)
    except Exception as e:
        return ok([])


# === 对话 ===

@router.post("/chat")
async def agent_chat(req: ChatRequest):
    harness = get_harness()
    llm = harness.registry.get("llm")
    if llm is None:
        raise HTTPException(503, "LLM plugin not loaded")

    system_prompt = (
        "你是自我成长助手，帮助用户管理日程和任务优先级。"
        "你可以通过 Searcher 搜索本地数据库和 MCP 外部知识库来查找文档和资料。"
        "用温暖鼓励的语气回复，每次回复添加情感标签 [CALM]/[ENCOURAGE]/[THINKING]/[URGENT]。"
        "当用户感到慌张时，给出当前任务的最优解决方案。"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for h in req.history:
                role = h.get("role", "user")
                if role == "agent":
                    role = "assistant"
                messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": req.message})

    optimized = harness.context_optimizer.optimize_messages(messages, system_prompt)

    try:
        resp = await llm.chat(optimized, max_tokens=4096)
        return ok({"reply": resp.content, "emotion_tag": resp.emotion_tag})
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(500, f"Chat failed: {e}")


@router.post("/chat/stream")
async def agent_chat_stream(req: ChatRequest):
    harness = get_harness()
    llm = harness.registry.get("llm")
    if llm is None:
        raise HTTPException(503, "LLM plugin not loaded")

    system_prompt = (
        "你是自我成长助手，帮助用户管理日程和任务优先级。"
        "用温暖鼓励的语气回复，每次回复添加情感标签 [CALM]/[ENCOURAGE]/[THINKING]/[URGENT]。"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for h in req.history:
                role = h.get("role", "user")
                if role == "agent":
                    role = "assistant"
                messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": req.message})

    optimized = harness.context_optimizer.optimize_messages(messages, system_prompt)

    async def generate():
        try:
            async for chunk in llm.chat_stream(optimized):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# === 优先级评估 ===

@router.post("/evaluate")
async def trigger_evaluation(db: Session = Depends(get_db)):
    harness = get_harness()
    priority = harness.registry.get("priority")
    if priority is None:
        raise HTTPException(503, "Priority engine not loaded")

    today = date.today()
    pending_todos = (
        db.query(TodoItem)
        .filter(TodoItem.date == today, TodoItem.status == "pending")
        .all()
    )

    result = {"evaluated": True, "tasks": [], "alerts": [], "message": "No pending tasks"}

    if not pending_todos:
        await _run_motivation(harness, result)
        return ok(result)

    tasks = [
        {"id": t.id, "content": t.content, "category": t.category, "importance": 8}
        for t in pending_todos
    ]

    context = {"current_time": str(date.today()), "_harness": harness}
    scored = await priority.evaluate(tasks, context)

    for s in scored:
        record = AgentTaskPriority(
            todo_id=s.todo_id,
            urgency_score=s.urgency_score,
            importance_score=s.importance_score,
            algorithm_score=s.algorithm_score,
            llm_score=s.llm_score,
            final_score=s.priority_score,
            llm_reasoning=s.llm_reasoning,
            suggested_action=s.suggested_action,
        )
        db.add(record)
    db.commit()

    alerts = []
    for s in scored:
        if priority.needs_alert(s):
            alerts.append({
                "task_id": s.todo_id,
                "content": s.content,
                "score": round(s.priority_score, 2),
                "suggested_action": s.suggested_action,
                "is_deadline_near": s.is_deadline_near,
            })

    if alerts:
        notifier = harness.registry.get("notify")
        if notifier:
            for alert in alerts:
                from backend.agent.plugins.notifier.base import Alert
                await notifier.notify(Alert(
                    title="任务提醒",
                    message=f"{alert['content']} - {alert['suggested_action']}",
                    level="urgent" if alert["score"] > 0.8 else "normal",
                    task_id=alert["task_id"],
                ))

    result = {
        "evaluated": True,
        "tasks": [
            {
                "id": s.todo_id,
                "content": s.content,
                "priority_score": round(s.priority_score, 3),
                "urgency": round(s.urgency_score, 3),
                "importance": round(s.importance_score, 3),
                "reasoning": s.llm_reasoning,
                "suggested_action": s.suggested_action,
                "needs_alert": priority.needs_alert(s),
            }
            for s in scored
        ],
        "alerts": alerts,
    }

    await _run_motivation(harness, result)
    return ok(result)


@router.get("/tasks/priority")
async def get_priority_tasks(db: Session = Depends(get_db)):
    today = date.today()
    from sqlalchemy import desc
    records = (
        db.query(AgentTaskPriority)
        .join(TodoItem)
        .filter(TodoItem.date == today)
        .order_by(desc(AgentTaskPriority.evaluated_at))
        .all()
    )

    seen = set()
    latest = []
    for r in records:
        if r.todo_id not in seen:
            seen.add(r.todo_id)
            todo = db.query(TodoItem).filter(TodoItem.id == r.todo_id).first()
            latest.append({
                "id": r.todo_id,
                "content": todo.content if todo else "",
                "category": todo.category if todo else "",
                "priority_score": round(r.final_score, 3),
                "urgency": round(r.urgency_score, 3),
                "importance": round(r.importance_score, 3),
                "reasoning": r.llm_reasoning,
                "suggested_action": r.suggested_action,
                "evaluated_at": str(r.evaluated_at),
            })

    latest.sort(key=lambda x: x["priority_score"], reverse=True)
    return ok({"tasks": latest})


# === TTS ===

@router.post("/tts")
async def text_to_speech(req: TTSRequest):
    harness = get_harness()
    tts = harness.registry.get("tts")
    if tts is None:
        raise HTTPException(503, "TTS engine not loaded")

    result = await _try_tts_with_fallback(harness, tts, req)
    if result is None:
        raise HTTPException(500, "TTS failed with all engines")
    from fastapi.responses import Response
    return Response(
        content=result.audio_data,
        media_type=f"audio/{result.format}",
    )


# === 调度器控制 ===

@router.get("/schedule/status")
async def schedule_status():
    harness = get_harness()
    if not hasattr(harness, '_scheduler'):
        return ok({"running": False, "cron": "*/20 * * * *", "next_run": None})
    return ok(harness._scheduler.get_status())


@router.post("/schedule/toggle")
async def toggle_schedule():
    harness = get_harness()
    scheduler = getattr(harness, '_scheduler', None)
    if scheduler is None:
        raise HTTPException(503, "Scheduler not initialized")

    if scheduler.is_running:
        scheduler.stop()
        return ok({"running": False, "message": "Scheduler stopped"})
    else:
        scheduler.start(harness._evaluate_and_notify)
        return ok({"running": True, "message": "Scheduler started"})


@router.put("/schedule/cron")
async def update_cron(req: CronUpdateRequest):
    harness = get_harness()
    scheduler = getattr(harness, '_scheduler', None)
    if scheduler is None:
        raise HTTPException(503, "Scheduler not initialized")

    success = scheduler.update_cron(req.cron)
    return ok({"success": success, "cron": req.cron})


# === 多 Agent 编排 ===

class OrchestrateRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)

_orchestrator = None


def set_orchestrator(orch) -> None:
    global _orchestrator
    _orchestrator = orch


@router.post("/orchestrate")
async def orchestrate(req: OrchestrateRequest):
    """多 Agent 编排: 自动分解任务 → 分派 Worker → 整合结果"""
    if _orchestrator is None:
        raise HTTPException(503, "Orchestrator not initialized")

    result = await _orchestrator.handle(req.message, req.history)
    return ok(result)


# === 智能日程插入 ===

class ScheduleRequest(BaseModel):
    message: str
    target_date: str | None = None  # YYYY-MM-DD, 不传则用今天
    history: list[dict] = Field(default_factory=list)


@router.post("/schedule")
async def schedule_tasks(req: ScheduleRequest, db: Session = Depends(get_db)):
    """智能日程插入：从对话中提取任务并写入数据库"""
    harness = get_harness()
    llm = harness.registry.get("llm")
    if llm is None:
        raise HTTPException(503, "LLM plugin not loaded")

    # 确定目标日期
    from datetime import date as date_type, datetime, timedelta
    today = date_type.today()

    if req.target_date:
        try:
            target_date = date_type.fromisoformat(req.target_date)
        except ValueError:
            target_date = today
    else:
        target_date = today

    # 构建 LLM 提示
    today_str = today.isoformat()
    target_str = target_date.isoformat()
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][target_date.weekday()]
    tomorrow_str = (today + timedelta(days=1)).isoformat()
    day_after_str = (today + timedelta(days=2)).isoformat()

    system_prompt = f"""你是日程解析助手。从用户消息中提取待办任务，输出纯 JSON（不要 markdown 代码块）。

当前日期: {today_str} ({["周一","周二","周三","周四","周五","周六","周日"][today.weekday()]})
目标日期: {target_str} ({weekday})
明天: {tomorrow_str}
后天: {day_after_str}

规则:
1. 如果用户提到"今天/明天/后天/周X"，推算为具体日期 YYYY-MM-DD
2. category 必须是以下之一: 学习/运动/工作/生活/阅读/冥想/其他
3. duration_minutes 根据上下文估算（默认 60）
4. 输出格式: {{"tasks": [{{"date": "YYYY-MM-DD", "content": "任务内容", "category": "分类", "duration_minutes": 分钟数}}]}}
5. 如果没有明确任务，返回 {{"tasks": []}}"""

    messages = [{"role": "system", "content": system_prompt}]
    for h in req.history[-4:]:  # 最近 4 条历史足够
        role = h.get("role", "user")
        if role == "agent":
            role = "assistant"
        messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": req.message})

    try:
        resp = await llm.chat(messages, temperature=0.2, max_tokens=2048)
    except Exception as e:
        logger.error(f"Schedule LLM failed: {e}")
        raise HTTPException(500, f"LLM failed: {e}")

    # 解析 JSON
    text = resp.content.strip()
    # 去掉可能的 markdown 代码块
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:]) if len(lines) > 1 else text
        if text.endswith("```"):
            text = text[:-3]

    import json as _json
    try:
        data = _json.loads(text)
    except _json.JSONDecodeError:
        # 尝试提取 JSON 块
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                data = _json.loads(text[start:end + 1])
            except _json.JSONDecodeError:
                return ok({"inserted": [], "message": "无法解析日程", "raw": text[:300]})
        else:
            return ok({"inserted": [], "message": "无法解析日程", "raw": text[:300]})

    tasks = data.get("tasks", [])
    if not tasks:
        return ok({"inserted": [], "message": "未检测到明确任务"})

    # 写入数据库
    from datetime import date as date_type
    inserted = []
    for t in tasks:
        try:
            task_date = date_type.fromisoformat(t["date"])
        except (KeyError, ValueError):
            task_date = target_date

        todo = TodoItem(
            date=task_date,
            content=t.get("content", ""),
            category=t.get("category", "其他"),
            duration_minutes=t.get("duration_minutes", 60),
            status="pending",
        )
        db.add(todo)
        db.commit()
        db.refresh(todo)
        inserted.append({
            "id": todo.id,
            "date": todo.date.isoformat(),
            "content": todo.content,
            "category": todo.category,
            "duration_minutes": todo.duration_minutes,
        })

    return ok({
        "inserted": inserted,
        "message": f"已添加 {len(inserted)} 条日程到 {target_str}",
    })


async def _run_motivation(harness, result: dict) -> None:
    """运行 MotivationEngine 并将结果注入 result"""
    try:
        from backend.agent.motivation_engine import MotivationEngine
        engine = MotivationEngine()
        notifier = harness.registry.get("notify")
        tts = harness.registry.get("tts")
        goal_alerts = await engine.tick(notifier, tts)
        result["goal_alerts"] = goal_alerts
    except Exception as e:
        logger.warning(f"MotivationEngine skipped: {e}")
        result["goal_alerts"] = []


# === 目标管理 (Goal CRUD) ===

class GoalCreate(BaseModel):
    title: str
    description: str = ""
    deadline: str | None = None
    target_metric: str = ""
    importance: int = 5


class GoalUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    deadline: str | None = None
    status: str | None = None
    target_metric: str | None = None
    current_progress: float | None = None
    importance: int | None = None


@router.get("/goals")
async def list_goals(status: str = "active", db: Session = Depends(get_db)):
    """列出目标"""
    from backend.models import Goal
    goals = db.query(Goal).filter(Goal.status == status).order_by(Goal.created_at.desc()).all()
    return ok([{
        "id": g.id, "title": g.title, "description": g.description,
        "deadline": g.deadline.isoformat() if g.deadline else None,
        "status": g.status, "target_metric": g.target_metric,
        "current_progress": g.current_progress, "importance": g.importance,
        "pressure": g.pressure, "reminder_count": g.reminder_count,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    } for g in goals])


@router.post("/goals")
async def create_goal(req: GoalCreate, db: Session = Depends(get_db)):
    """创建目标"""
    from backend.models import Goal
    from datetime import date as date_type
    deadline = date_type.fromisoformat(req.deadline) if req.deadline else None
    goal = Goal(
        title=req.title, description=req.description,
        deadline=deadline, target_metric=req.target_metric,
        importance=req.importance,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return ok({
        "id": goal.id, "title": goal.title,
        "deadline": goal.deadline.isoformat() if goal.deadline else None,
    })


@router.get("/goals/{goal_id}")
async def get_goal(goal_id: int, db: Session = Depends(get_db)):
    """获取目标详情（含子任务）"""
    from backend.models import Goal, GoalTask
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    tasks = [{
        "id": t.id, "content": t.content, "category": t.category,
        "status": t.status, "daily_quota": t.daily_quota,
        "today_progress": t.today_progress,
    } for t in goal.tasks]
    return ok({
        "id": goal.id, "title": goal.title, "description": goal.description,
        "deadline": goal.deadline.isoformat() if goal.deadline else None,
        "status": goal.status, "target_metric": goal.target_metric,
        "current_progress": goal.current_progress, "importance": goal.importance,
        "pressure": goal.pressure, "reminder_count": goal.reminder_count,
        "tasks": tasks,
    })


@router.put("/goals/{goal_id}")
async def update_goal(goal_id: int, req: GoalUpdate, db: Session = Depends(get_db)):
    """更新目标"""
    from backend.models import Goal
    from datetime import date as date_type
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    for field in ["title", "description", "status", "target_metric", "importance"]:
        val = getattr(req, field, None)
        if val is not None:
            setattr(goal, field, val)
    if req.deadline is not None:
        goal.deadline = date_type.fromisoformat(req.deadline) if req.deadline else None
    if req.current_progress is not None:
        goal.current_progress = req.current_progress
    db.commit()
    return ok({"updated": True})


@router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    """删除目标"""
    from backend.models import Goal
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    db.delete(goal)
    db.commit()
    return ok({"deleted": True})


# ═══ 在线监控 API ═══

@router.get("/monitor/summary")
async def get_monitor_summary():
    """获取在线监控摘要: 4维度一览

    Returns: 质量/异常/成本延迟/安全 四个维度的最近状态
    """
    from backend.database import SessionLocal
    from backend.models import AgentMetrics, AgentAnomaly, AgentQualitySample, AgentSafetyLog
    from datetime import date, timedelta
    from sqlalchemy import func

    db = SessionLocal()
    try:
        today = date.today()

        # 1. 质量: 最近质量抽样均值
        quality_row = db.query(
            func.count().label("cnt"),
            func.avg(AgentQualitySample.quality_score).label("avg"),
        ).filter(AgentQualitySample.created_at >= today).first()

        # 2. 异常: 今日未确认的异常数
        anomaly_count = db.query(func.count()).filter(
            AgentAnomaly.created_at >= today,
            AgentAnomaly.acknowledged == False,
        ).scalar() or 0

        # 3. 成本/延迟: 最近7天
        since = today - timedelta(days=7)
        metrics_rows = db.query(AgentMetrics).filter(
            AgentMetrics.date >= since
        ).all()

        total_tokens = sum(r.total_token_estimate for r in metrics_rows)
        total_calls = sum(r.total_calls for r in metrics_rows)
        avg_lat = int(sum(r.avg_latency_ms for r in metrics_rows if r.avg_latency_ms) / max(len([r for r in metrics_rows if r.avg_latency_ms]), 1))
        estimated_cost = round(total_tokens * 0.000002, 4)  # ~$2/M tokens

        # 4. 安全: 今日安全分均值 + 违规数
        safety_row = db.query(
            func.count().label("cnt"),
            func.avg(AgentSafetyLog.safety_score).label("avg"),
            func.sum(func.case((AgentSafetyLog.jailbreak_attempt == True, 1), else_=0)).label("jailbreaks"),
            func.sum(func.case((AgentSafetyLog.harmful_content == True, 1), else_=0)).label("harmful"),
        ).filter(AgentSafetyLog.created_at >= today).first()

        return ok({
            "quality": {
                "recent_samples": quality_row.cnt or 0,
                "avg_score": round(quality_row.avg or 0, 1),
                "status": "healthy" if (quality_row.avg or 5) >= 3.5 else "degraded",
            },
            "anomalies": {
                "today_count": anomaly_count,
                "status": "clear" if anomaly_count == 0 else "alert",
            },
            "cost_efficiency": {
                "7d_total_calls": total_calls,
                "7d_total_tokens": total_tokens,
                "7d_estimated_cost_usd": estimated_cost,
                "7d_avg_latency_ms": avg_lat,
                "status": "normal" if avg_lat < 5000 else "slow",
            },
            "safety": {
                "today_scans": safety_row.cnt or 0,
                "avg_score": round(safety_row.avg or 100, 0),
                "jailbreak_attempts": safety_row.jailbreaks or 0,
                "harmful_detections": safety_row.harmful or 0,
                "status": "safe" if (safety_row.avg or 100) >= 90 else "warning",
            },
        })
    finally:
        db.close()


@router.get("/monitor/anomalies")
async def get_anomalies(limit: int = 20):
    """获取最近的异常事件列表"""
    from backend.agent.observability.monitor import Monitor
    monitor = Monitor()
    return ok(monitor.get_recent_anomalies(limit=limit))


@router.get("/monitor/quality-trend")
async def get_quality_trend(days: int = 7):
    """获取质量趋势数据"""
    from backend.database import SessionLocal
    from backend.models import AgentQualitySample
    from datetime import date, timedelta
    from sqlalchemy import func

    db = SessionLocal()
    try:
        since = date.today() - timedelta(days=days)
        rows = db.query(
            func.date(AgentQualitySample.created_at).label("d"),
            func.count().label("cnt"),
            func.avg(AgentQualitySample.quality_score).label("avg"),
        ).filter(AgentQualitySample.created_at >= since).group_by("d").order_by("d").all()

        return ok([{
            "date": r.d.isoformat() if r.d else "",
            "sample_count": r.cnt,
            "avg_score": round(r.avg or 0, 1),
        } for r in rows])
    finally:
        db.close()


@router.get("/monitor/safety-log")
async def get_safety_log(limit: int = 20, severity: str = ""):
    """获取安全日志列表"""
    from backend.database import SessionLocal
    from backend.models import AgentSafetyLog

    db = SessionLocal()
    try:
        q = db.query(AgentSafetyLog)
        if severity == "flagged":
            q = q.filter(AgentSafetyLog.safety_score < 100)
        rows = q.order_by(AgentSafetyLog.created_at.desc()).limit(limit).all()

        return ok([{
            "id": r.id,
            "orchestration_id": r.orchestration_id,
            "safety_score": r.safety_score,
            "jailbreak_attempt": r.jailbreak_attempt,
            "pii_detected": r.pii_detected,
            "harmful_content": r.harmful_content,
            "user_message_preview": r.user_message[:100],
            "created_at": r.created_at.isoformat() if r.created_at else "",
        } for r in rows])
    finally:
        db.close()


@router.post("/monitor/rebuild-baseline")
async def rebuild_monitor_baseline():
    """手动重建监控基线"""
    from backend.agent.observability.monitor import Monitor
    monitor = Monitor()
    result = monitor.rebuild_baseline()
    return ok({"rebuilt": len(result), "agents": list(result.keys())})


@router.post("/monitor/check")
async def trigger_monitor_check():
    """手动触发基线异常检查"""
    from backend.agent.observability.monitor import Monitor
    from datetime import date
    monitor = Monitor()
    anomalies = monitor.check_baseline(date.today())
    return ok({
        "anomalies_found": len(anomalies),
        "anomalies": anomalies,
    })
