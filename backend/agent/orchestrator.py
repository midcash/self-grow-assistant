"""Orchestrator — 多 Agent 编排核心

Supervisor-Worker 模式:
1. 分析用户意图 → 任务分解
2. 匹配 Worker → 并行/顺序分派
3. 汇总 Worker 结果 → 整合输出

通用设计: 不绑定特定领域，LLM 自主决定如何拆分和路由
"""

import asyncio
import json
import logging
from datetime import date
from typing import Any

from backend.agent.workers.base import TaskBrief, WorkerResult
from backend.agent.workers.searcher import SearcherWorker
from backend.agent.workers.profiler import ProfilerWorker
from backend.agent.workers.scheduler_worker import SchedulerWorker
from backend.agent.workers.goal_decomposer import GoalDecomposerWorker
from backend.agent.workers.coach import CoachWorker

logger = logging.getLogger(__name__)

# Worker 注册表
WORKER_REGISTRY = {
    "searcher": SearcherWorker,
    "profiler": ProfilerWorker,
    "executor": SchedulerWorker,
    "goal_decomposer": GoalDecomposerWorker,
    "coach": CoachWorker,
}

# Worker → 能力关键词映射（用于 LLM 路由）
CAPABILITY_KEYWORDS = {
    "searcher": ["搜索", "查找", "查询", "检索", "信息", "资料", "了解", "research", "search", "find", "lookup", "景点", "餐厅", "路线", "推荐", "攻略", "知识"],
    "profiler": ["偏好", "习惯", "画像", "分析", "水平", "能力", "状态", "总结", "历史", "花销", "预算", "风格", "profile", "analyze"],
    "executor": ["创建", "添加", "写入", "日程", "安排", "计划", "TODO", "提醒", "schedule", "create", "insert", "add"],
    "goal_decomposer": ["分解", "拆解", "规划目标", "目标分解", "拆分任务", "decompose", "breakdown"],
    "coach": ["心理", "辅导", "焦虑", "紧张", "压力大", "自卑", "害怕", "担心", "鼓励", "安慰", "帮助我", "难过", "沮丧", "慌张"],
}


class Orchestrator:
    """多 Agent 编排器

    用法:
        orch = Orchestrator(llm_plugin)
        result = await orch.handle("帮我安排明天的工作")
    """

    def __init__(self, llm_plugin):
        self._llm = llm_plugin
        self._workers: dict[str, Any] = {}

        # 在线监控钩子(延迟初始化)
        self._safety_scanner = None
        self._quality_sampler = None

    def _ensure_monitors(self):
        """延迟初始化监控组件(需要LLM就绪后)"""
        if self._safety_scanner is None:
            from backend.agent.observability.safety import SafetyScanner
            self._safety_scanner = SafetyScanner()
        if self._quality_sampler is None:
            from backend.agent.observability.quality_sampler import QualitySampler
            self._quality_sampler = QualitySampler(self._llm, sampling_rate=10)

    async def warmup(self) -> None:
        """初始化所有 Worker（注入 LLM）"""
        for name, cls in WORKER_REGISTRY.items():
            worker = cls()
            worker.set_llm(self._llm)
            self._workers[name] = worker
        logger.info(f"Orchestrator ready, workers: {list(self._workers.keys())}")

    async def handle(self, user_message: str,
                     chat_history: list[dict] | None = None) -> dict:
        """主入口: 处理用户请求"""
        import time as time_module
        t_start = time_module.time()
        chat_history = chat_history or []

        # 初始化结构化 Trace
        from backend.agent.observability.tracer import get_tracer
        tracer = get_tracer()
        orch_id = tracer.start_orchestration(user_message[:200])

        # Step 1: 意图分析 + 任务分解
        t_plan_start = time_module.time()
        plan = await self._plan(user_message, chat_history)
        plan_elapsed_ms = round((time_module.time() - t_plan_start) * 1000)
        intent = plan.get("intent", "general")
        subtasks = plan.get("subtasks", [])
        reply_intro = plan.get("reply_intro", "")

        logger.info(f"Orchestrator plan: intent={intent}, subtasks={len(subtasks)}")

        # Trace: plan span
        tracer.record_span(
            orchestration_id=orch_id, span_type="plan",
            agent_name="orchestrator", objective=intent,
            input_summary=user_message[:300],
            output_summary=json.dumps({"intent": intent, "subtask_count": len(subtasks)}, ensure_ascii=False)[:500],
            latency_ms=plan_elapsed_ms, success=True,
        )

        # Step 2: 如果没有子任务 → 直接 LLM 回复
        if not subtasks:
            reply = await self._direct_reply(user_message, chat_history)
            total_ms = round((time_module.time() - t_start) * 1000)
            tracer.record_span(orchestration_id=orch_id, span_type="synthesis",
                agent_name="orchestrator", objective="direct_reply",
                output_summary=reply[:300], latency_ms=0, success=True)
            tracer.flush()
            self._log_plan(plan, plan_elapsed_ms, [], [], total_ms, user_message, reply)
            return {"reply": reply, "workers_used": [], "plan": plan}

        # Step 3: 并行执行独立子任务
        parallel_tasks = [s for s in subtasks if not s.get("depends_on")]
        dependent_tasks = [s for s in subtasks if s.get("depends_on")]

        async def _timed(task):
            t0 = time_module.time()
            r = await self._execute_subtask(task)
            ms = round((time_module.time() - t0) * 1000)
            task["_elapsed_ms"] = ms
            task["_success"] = r.success
            # Trace: worker_execute span
            tracer.record_span(
                orchestration_id=orch_id, span_type="worker_execute",
                agent_name=task.get("id", "unknown"),
                objective=task.get("objective", "")[:200],
                input_summary=json.dumps({"task_id": task.get("id"), "constraints": task.get("constraints", [])}, ensure_ascii=False)[:500],
                output_summary=r.content[:300],
                latency_ms=ms, success=r.success,
                error_message="" if r.success else r.content[:300],
                metadata=json.dumps({"confidence": r.confidence, "sources": r.sources}, ensure_ascii=False),
            )
            return r

        if parallel_tasks:
            results = await asyncio.gather(
                *[_timed(s) for s in parallel_tasks],
                return_exceptions=True,
            )
            results = [
                r if isinstance(r, WorkerResult) else WorkerResult(
                    task_id="error", success=False, content=str(r), confidence=0
                )
                for r in results
            ]

        # Step 4: 执行依赖任务（拿到前序结果后）
        for dep_task in dependent_tasks:
            dep_id = dep_task.get("depends_on")
            dep_result = next((r for r in results if r.task_id == dep_id), None)
            if dep_result and dep_result.success:
                dep_task["context"] = (dep_task.get("context", "") +
                                       "\n" + dep_result.content)
            r = await _timed(dep_task)
            results.append(r)

        # Step 5: 整合所有结果
        t_syn_start = time_module.time()
        synthesis = await self._synthesize(intent, user_message, results, reply_intro)
        syn_elapsed_ms = round((time_module.time() - t_syn_start) * 1000)
        tracer.record_span(orchestration_id=orch_id, span_type="synthesis",
            agent_name="orchestrator", objective="synthesize",
            output_summary=synthesis[:300], latency_ms=syn_elapsed_ms, success=True)

        # Step 5.5: MicroCompact
        self._micro_compact(results)

        # Step 5.6: 在线监控 — 安全扫描 + 质量抽样
        self._ensure_monitors()

        # 安全扫描(同步, 规则匹配, 耗时<1ms)
        workers_used_names = [r.task_id for r in results if r.success]
        safety_result = None
        try:
            safety_result = self._safety_scanner.scan(
                orchestration_id=orch_id,
                user_message=user_message,
                agent_reply=synthesis,
            )
        except Exception as e:
            logger.warning(f"Safety scan failed: {e}")

        # 质量抽样(异步触发, 命中采样率才评分)
        quality_result = None
        try:
            quality_result = await self._quality_sampler.maybe_sample(
                orchestration_id=orch_id,
                user_message=user_message,
                agent_reply=synthesis,
                workers_used=workers_used_names,
            )
        except Exception as e:
            logger.warning(f"Quality sampling failed: {e}")

        # Token估算(字符数/2.5 ≈ 中文token, /4 ≈ 英文token)
        total_chars = len(user_message) + len(synthesis)
        estimated_tokens = max(1, int(total_chars / 3))
        estimated_cost = round(estimated_tokens * 0.000002, 6)  # ~$2/M tokens

        # 监控摘要写入synthesis span metadata
        monitor_meta = {
            "tokens_estimate": estimated_tokens,
            "cost_estimate": estimated_cost,
        }
        if safety_result:
            monitor_meta["safety_score"] = safety_result["safety_score"]
            monitor_meta["safety_flags"] = len(safety_result["flags"])
        if quality_result:
            monitor_meta["quality_score"] = quality_result["quality_score"]

        # Step 6: 沉淀到记忆层
        t_persist_start = time_module.time()
        await self._persist_to_memory(intent, user_message, results, synthesis)
        persist_elapsed_ms = round((time_module.time() - t_persist_start) * 1000)
        tracer.record_span(orchestration_id=orch_id, span_type="persist",
            agent_name="orchestrator", objective="persist_to_memory",
            latency_ms=persist_elapsed_ms, success=True)

        # Step 7: 路由可观测性日志
        total_elapsed_ms = round((time_module.time() - t_start) * 1000)
        self._log_plan(plan, plan_elapsed_ms, parallel_tasks, dependent_tasks,
                       total_elapsed_ms, user_message, synthesis)

        # 写入所有结构化 Trace
        tracer.flush()

        return {
            "reply": synthesis,
            "workers_used": workers_used_names,
            "results": [
                {"role": r.task_id, "success": r.success, "summary": r.content[:200]}
                for r in results
            ],
            "plan": plan,
            "monitoring": {
                "safety": safety_result,
                "quality": quality_result,
                "tokens_estimated": estimated_tokens,
                "cost_estimated": estimated_cost,
            },
        }

    async def _persist_to_memory(self, intent: str, user_message: str,
                                  results: list[WorkerResult],
                                  synthesis: str) -> None:
        """将本次编排结果写入三层记忆"""
        today = date.today()

        # ── Warm Memory: SQLite ──
        try:
            from backend.database import SessionLocal
            from backend.models import AgentMemoryDigest, AgentConversation
            from datetime import datetime

            db = SessionLocal()
            try:
                # 保存对话记录
                db.add(AgentConversation(role="user", content=user_message))
                db.add(AgentConversation(
                    role="agent",
                    content=synthesis[:500],
                    emotion_tag="THINKING" if results else "CALM",
                ))

                # 更新/创建每日摘要
                existing = db.query(AgentMemoryDigest).filter(
                    AgentMemoryDigest.date == today
                ).first()

                worker_summaries = "\n".join(
                    f"- [{r.task_id}] {'OK' if r.success else 'FAIL'}: {r.content[:200]}"
                    for r in results if r.task_id != "error"
                )
                summary_text = (
                    f"## {today.isoformat()} 编排记录\n"
                    f"意图: {intent}\n"
                    f"用户: {user_message[:200]}\n"
                    f"Worker 执行:\n{worker_summaries}\n"
                    f"回复摘要: {synthesis[:300]}"
                )

                if existing:
                    existing.summary = summary_text
                    existing.pending_count = len([r for r in results if not r.success])
                    existing.completed_count = len([r for r in results if r.success])
                else:
                    db.add(AgentMemoryDigest(
                        date=today,
                        summary=summary_text,
                        completed_count=len([r for r in results if r.success]),
                        pending_count=len([r for r in results if not r.success]),
                        top_priority_task=user_message[:200],
                    ))
                db.commit()
                logger.info("Warm memory (SQLite) updated")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Warm memory write failed: {e}")

        # ── Cold Memory: Markdown ──
        try:
            from pathlib import Path
            digest_dir = Path("data/agent-memory/digest")
            digest_dir.mkdir(parents=True, exist_ok=True)

            worker_details = "\n".join(
                f"### {r.task_id}\n- 成功: {r.success}\n"
                f"- 来源: {', '.join(r.sources) if r.sources else '无'}\n"
                f"- 置信度: {r.confidence}\n"
                f"- 内容:\n{r.content[:800]}"
                for r in results if r.task_id != "error"
            )

            md = (
                f"# {today.isoformat()} — {intent}\n\n"
                f"## 用户请求\n{user_message}\n\n"
                f"## Worker 执行详情\n{worker_details}\n\n"
                f"## 最终回复\n{synthesis}\n"
            )
            (digest_dir / f"{today.isoformat()}-{intent}.md").write_text(
                md, encoding="utf-8"
            )

            # 更新 index
            index_path = Path("data/agent-memory/index.md")
            entry = f"- [{today.isoformat()} {intent}](digest/{today.isoformat()}-{intent}.md)"
            if index_path.exists():
                content = index_path.read_text(encoding="utf-8")
                if entry not in content:
                    lines = content.strip().split("\n")
                    lines.insert(1, entry)
                    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            else:
                index_path.write_text(
                    f"# Agent Memory Index\n\n{entry}\n", encoding="utf-8"
                )

            logger.info("Cold memory (Markdown) written")
        except Exception as e:
            logger.warning(f"Cold memory write failed: {e}")

    def _micro_compact(self, results: list[WorkerResult]) -> None:
        """MicroCompact: 截断 Worker 长结果到 200 字，释放上下文空间。

        参考 Claude Code MicroCompact:
        - 零 LLM 调用，纯截断
        - 完整数据已在 Cold Memory (Markdown) 中保留
        - 只清理 Worker 输出，不碰用户消息
        """
        for r in results:
            if len(r.content) > 200:
                r.content = r.content[:200] + "..."

    def _log_plan(self, plan: dict, plan_elapsed_ms: int,
                  parallel_tasks: list, dependent_tasks: list,
                  total_elapsed_ms: int, user_message: str,
                  synthesis: str) -> None:
        """路由可观测性：每次编排后写入计划日志"""
        try:
            from pathlib import Path
            from datetime import datetime

            log_dir = Path("data/agent-memory/plan-logs")
            log_dir.mkdir(parents=True, exist_ok=True)

            now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            # Worker 执行明细
            all_tasks = parallel_tasks + dependent_tasks
            worker_rows = ""
            for t in all_tasks:
                wid = t.get("id", "?")
                obj = t.get("objective", "")[:80]
                elapsed = t.get("_elapsed_ms", "?")
                success = "OK" if t.get("_success") else "FAIL"
                worker_rows += f"| {wid} | {obj} | {elapsed}ms | {success} |\n"

            md = f"""# 编排日志 — {now}

## LLM 计划 ({plan_elapsed_ms}ms)
```json
{json.dumps(plan, ensure_ascii=False, indent=2)}
```

## Worker 执行
| Worker | 目标 | 耗时 | 结果 |
|--------|------|------|------|
{worker_rows}

## 最终回复
{synthesis[:500]}

## 汇总
| 指标 | 值 |
|------|-----|
| 总耗时 | {total_elapsed_ms}ms |
| 计划阶段 | {plan_elapsed_ms}ms |
| Worker 数 | {len(all_tasks)} |
| 成功/失败 | {sum(1 for t in all_tasks if t.get('_success'))}/{sum(1 for t in all_tasks if not t.get('_success'))} |
| 用户消息 | {user_message[:200]} |
"""
            filename = f"{now[:19].replace(':', '-')}-{plan.get('intent', 'general')}.md"
            (log_dir / filename).write_text(md, encoding="utf-8")
            logger.info(f"Plan log written: {filename}")
        except Exception as e:
            logger.warning(f"Plan log write failed: {e}")

    async def _plan(self, message: str, history: list[dict]) -> dict:
        """LLM 分析意图并生成执行计划"""
        today = date.today()
        worker_descriptions = []
        for name, keywords in CAPABILITY_KEYWORDS.items():
            worker_descriptions.append(f"- {name}: {', '.join(keywords[:8])}")

        system = f"""你是任务编排专家。分析用户请求，决定需要调用哪些 Worker 来完成。

可用 Worker:
{chr(10).join(worker_descriptions)}

今天日期: {today.isoformat()}

规则:
1. 如果请求简单、不需要搜索/画像/写数据库 → subtasks 返回空数组
2. 如果有明确的信息检索需求 → 创建 searcher 子任务
3. 如果需要了解用户偏好/习惯 → 创建 profiler 子任务
4. 如果需要创建日程/写入数据 → 创建 executor 子任务
4b. 如果需要分解目标/规划任务 → 创建 goal_decomposer 子任务
4c. 如果用户表达情绪困扰/焦虑/压力/自卑 → 创建 coach 子任务
5. 子任务可以并行执行（不相互依赖）
6. 当前不联网搜索，searcher 只能查本地数据库和 LLM 知识

输出纯 JSON (无 markdown):
{{"intent": "意图类型", "reply_intro": "给用户的简短开头语", "subtasks": [{{"id": "searcher", "objective": "搜索什么", "context": "上下文", "expected_format": "text或json", "max_retries": 2, "timeout_seconds": 30}}]}}
- max_retries: 默认 2，复杂查询可用 3
- timeout_seconds: 默认 30，数据库查询 15 即可，LLM 补充可用 60
- expected_format: 纯信息检索用 "text"，需要结构化数据用 "json" """

        messages = [{"role": "system", "content": system}]
        for h in history[-4:]:
            role = h.get("role", "user")
            if role == "agent": role = "assistant"
            messages.append({"role": role, "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

        try:
            resp = await self._llm.chat(messages, temperature=0.2, max_tokens=1024)
            raw = resp.content.strip()
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end != -1:
                return json.loads(raw[start:end + 1])
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Plan parsing failed: {e}")

        # Fallback: 简单意图推断
        return self._rule_based_plan(message)

    def _rule_based_plan(self, message: str) -> dict:
        """基于规则的意图推断（LLM 失败时降级）"""
        subtasks = []
        for worker_name, keywords in CAPABILITY_KEYWORDS.items():
            if any(kw in message for kw in keywords):
                subtasks.append({
                    "id": worker_name,
                    "objective": message,
                    "context": "",
                })

        return {
            "intent": "general",
            "reply_intro": "",
            "subtasks": subtasks or [],
        }

    async def _execute_subtask(self, task: dict) -> WorkerResult:
        """执行单个子任务"""
        worker_name = task.get("id", "")
        worker = self._workers.get(worker_name)

        if not worker:
            return WorkerResult(
                task_id=worker_name,
                success=False,
                content=f"未找到 Worker: {worker_name}",
                confidence=0,
            )

        brief = TaskBrief(
            task_id=worker_name,
            objective=task.get("objective", ""),
            context=task.get("context", ""),
            constraints=task.get("constraints", []),
            expected_format=task.get("expected_format", "text"),
            output_schema=task.get("output_schema"),
            max_retries=task.get("max_retries", 2),
            timeout_seconds=task.get("timeout_seconds", 30),
        )

        logger.info(f"Dispatch → {worker_name}: {brief.objective[:60]}...")
        return await worker.execute_with_retry(brief)

    async def _synthesize(self, intent: str, original_message: str,
                          results: list[WorkerResult],
                          reply_intro: str = "") -> str:
        """整合 Worker 结果，生成最终回复"""
        # 汇总成功结果
        success_results = [r for r in results if r.success]
        if not success_results:
            return "抱歉，暂时无法完成这个请求。请稍后再试。"

        # 构建整合提示
        worker_outputs = "\n\n".join(
            f"[{r.task_id} Worker 结果]:\n{r.content}"
            for r in success_results
        )

        system = f"""你是个人助手，负责整合多个专业 Worker 的结果，给用户一个完整、自然的回复。

规则:
1. 不要重复 Worker 的原始数据，提炼要点
2. 如果涉及日程建议，询问用户是否需要写入
3. 语气温暖鼓励
4. 结尾添加情感标签 [ENCOURAGE]/[THINKING] 等
5. 回复简洁，控制在 200 字以内"""

        msg = (
            f"用户原始请求: {original_message}\n\n"
            f"Worker 分析结果:\n{worker_outputs}\n\n"
            f"{reply_intro}\n"
            f"请整合以上信息，给用户一个完整的回复。"
        )

        try:
            resp = await self._llm.chat(
                [{"role": "system", "content": system},
                 {"role": "user", "content": msg}],
                max_tokens=1024, temperature=0.5,
            )
            return resp.content
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return reply_intro + "\n\n" + "\n".join(r.content[:200] for r in success_results)

    async def _direct_reply(self, message: str,
                            history: list[dict]) -> str:
        """简单请求直接 LLM 回复，不走 Worker"""
        system = (
            "你是自我成长助手，帮助用户管理日程和任务优先级。"
            "用温暖鼓励的语气回复。"
        )
        messages = [{"role": "system", "content": system}]
        for h in history[-4:]:
            role = h.get("role", "user")
            if role == "agent": role = "assistant"
            messages.append({"role": role, "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

        try:
            resp = await self._llm.chat(messages, max_tokens=1024)
            return resp.content
        except Exception:
            return "好的，我理解了。"

    async def shutdown(self) -> None:
        self._workers.clear()
