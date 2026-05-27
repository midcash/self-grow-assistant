"""Scheduler Worker — 日程执行 Agent

能力: 创建日程、写入 TODO、触发优先级评估
工具: todo_items CRUD、AgentTaskPriority 写入
特性: 可无 LLM 运行（纯函数），也可用 LLM 理解模糊指令
"""

import logging
from datetime import date, timedelta

from backend.agent.workers.base import WorkerBase, WorkerResult, TaskBrief

logger = logging.getLogger(__name__)


class SchedulerWorker(WorkerBase):
    """日程执行 Agent

    负责将结构化任务写入数据库:
    - 创建 TODO 条目
    - 设定日期、类别、时长
    - 触发优先级评估
    """

    @property
    def role(self) -> str:
        return "executor"

    @property
    def system_prompt(self) -> str:
        return """你是日程执行专家。负责将任务计划转化为具体的日程条目。

你的工作方式:
1. 理解需要创建的任务
2. 将任务解析为: 日期、内容、类别、时长
3. 确认后写入日程数据库
4. 返回创建结果

输出要求:
- JSON 格式: {"tasks": [{"date": "YYYY-MM-DD", "content": "...", "category": "...", "duration_minutes": N}]}
- category 必须是: 学习/运动/工作/生活/阅读/冥想/其他"""

    def capabilities(self) -> list[str]:
        return ["schedule", "create_task", "write", "insert", "add_todo"]

    async def execute(self, brief: TaskBrief) -> WorkerResult:
        """执行日程创建"""
        try:
            tasks_to_create = []

            # 如果已有结构化数据
            if brief.context and isinstance(brief.context, dict):
                tasks_to_create = brief.context.get("tasks", [])

            # 否则用 LLM 解析
            if not tasks_to_create and self._llm:
                tasks_to_create = await self._parse_with_llm(brief)

            if not tasks_to_create:
                return WorkerResult(
                    task_id=brief.task_id,
                    success=False,
                    content="未检测到可创建的日程条目",
                    confidence=0.0,
                )

            # 写入数据库
            created = self._create_todos(tasks_to_create)

            # 格式化确认
            lines = [f"## 日程已创建 ({len(created)}条)\n"]
            for item in created:
                lines.append(
                    f"- {item['date']} | {item['content']} "
                    f"({item['category']}, {item['duration_minutes']}分钟)"
                )

            return WorkerResult(
                task_id=brief.task_id,
                success=True,
                content="\n".join(lines),
                data={"created": created},
                sources=["数据库写入"],
                confidence=0.95,
            )
        except Exception as e:
            logger.error(f"Scheduler failed: {e}")
            return WorkerResult(
                task_id=brief.task_id,
                success=False,
                content=f"日程创建失败: {e}",
                confidence=0.0,
            )

    def _create_todos(self, tasks: list[dict]) -> list[dict]:
        """写入数据库"""
        from backend.database import SessionLocal
        from backend.models import TodoItem

        db = SessionLocal()
        created = []
        try:
            today = date.today()
            for t in tasks:
                task_date = today
                if "date" in t:
                    try:
                        task_date = date.fromisoformat(t["date"])
                    except (ValueError, TypeError):
                        pass

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
                created.append({
                    "id": todo.id,
                    "date": todo.date.isoformat(),
                    "content": todo.content,
                    "category": todo.category,
                    "duration_minutes": todo.duration_minutes,
                })
        finally:
            db.close()

        logger.info(f"Scheduler created {len(created)} todos")
        return created

    async def _parse_with_llm(self, brief: TaskBrief) -> list[dict]:
        """用 LLM 解析模糊任务为结构化日程"""
        today = date.today()
        tomorrow = today + timedelta(days=1)

        msg = (
            f"目标: {brief.objective}\n"
            f"上下文: {brief.context}\n"
            f"今天: {today.isoformat()}, 明天: {tomorrow.isoformat()}\n"
            f"请将以上内容转化为具体的日程条目 (JSON 格式)。"
        )

        try:
            result = await self._call_llm(
                [{"role": "system", "content": self.system_prompt},
                 {"role": "user", "content": msg}],
                max_tokens=1024, temperature=0.2,
            )
            import json
            # 提取 JSON
            start = result.find("{")
            end = result.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(result[start:end + 1])
                return data.get("tasks", [])
        except Exception as e:
            logger.warning(f"LLM parse failed: {e}")

        return []
