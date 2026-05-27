"""GoalDecomposer Agent — 目标分解 Worker

将长期目标递归分解为可执行的子任务树。
参考 APEX Agent 的三层分解: 战略 → 战术 → 操作
"""

import json
import logging
from datetime import date, timedelta

from backend.agent.workers.base import WorkerBase, WorkerResult, TaskBrief

logger = logging.getLogger(__name__)


class GoalDecomposerWorker(WorkerBase):
    """目标分解 Agent

    职责: 将模糊的长期目标分解为具体可执行的子任务
    三层分解:
      战略层: 目标 → 3-5 个子目标
      战术层: 子目标 → 具体任务 + 分类 + 每日配额
      操作层: 写入 GoalTask + TodoItem
    """

    @property
    def role(self) -> str:
        return "goal_decomposer"

    @property
    def system_prompt(self) -> str:
        return """你是目标分解专家。将长期目标拆解为具体可执行的子任务。

你的工作方式:
1. 理解目标的最终交付物
2. 按时间倒推分解为阶段性子目标
3. 每个子目标拆解为每日可执行的小任务
4. 输出结构化 JSON，供系统自动创建任务

输出格式:
{
  "subgoals": [
    {
      "title": "子目标标题",
      "tasks": [
        {"content": "任务内容", "category": "学习/工作/生活/其他", "daily_quota": "每日应完成量"},
      ]
    }
  ]
}

category 必须是: 学习 / 工作 / 生活 / 阅读 / 冥想 / 其他"""

    def capabilities(self) -> list[str]:
        return ["decompose", "breakdown", "plan", "拆分", "分解", "规划"]

    async def execute(self, brief: TaskBrief) -> WorkerResult:
        try:
            today = date.today()
            deadline_str = brief.context or "未知"
            goal_title = brief.objective

            prompt = f"""请将以下目标分解为子任务:
目标: {goal_title}
截止日期: {deadline_str}
今天日期: {today.isoformat()}

要求:
1. 先输出 3-5 个子目标（战略层）
2. 每个子目标拆解 2-4 个具体任务（战术层）
3. 每个任务标注分类和每日配额
4. 任务应该是可在 1-2 小时内完成的粒度
5. 优先安排靠近日期的子目标"""

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ]

            try:
                raw = await self._call_llm(messages, max_tokens=2048, temperature=0.3)
            except Exception:
                return WorkerResult(
                    task_id=brief.task_id, success=False,
                    content="LLM 调用失败，无法分解目标",
                    confidence=0.0,
                )

            # 解析 JSON
            start, end = raw.find("{"), raw.rfind("}")
            if start == -1 or end == -1:
                return WorkerResult(
                    task_id=brief.task_id, success=False,
                    content=f"LLM 返回格式异常，无法解析 JSON",
                    confidence=0.0,
                )

            try:
                plan = json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                return WorkerResult(
                    task_id=brief.task_id, success=False,
                    content=f"JSON 解析失败",
                    confidence=0.0,
                )

            subgoals = plan.get("subgoals", [])
            if not subgoals:
                return WorkerResult(
                    task_id=brief.task_id, success=True,
                    content="该目标较简单，无需分解。可以直接作为一个任务。",
                    data={"subgoals": []},
                    confidence=0.8,
                )

            # 写入数据库
            created = self._write_goal_tasks(brief.task_id, subgoals, today)

            lines = [f"## 目标分解: {goal_title}\n"]
            for sg in subgoals:
                lines.append(f"### {sg['title']}")
                for t in sg.get("tasks", []):
                    lines.append(f"- [{t.get('category', '其他')}] {t['content']} (每日: {t.get('daily_quota', '适量')})")

            return WorkerResult(
                task_id=brief.task_id,
                success=True,
                content="\n".join(lines),
                data={"subgoals": subgoals, "created": created},
                sources=["LLM 分解"],
                confidence=0.85,
            )

        except Exception as e:
            logger.error(f"GoalDecomposer failed: {e}")
            return WorkerResult(
                task_id=brief.task_id, success=False,
                content=f"分解失败: {e}",
                confidence=0.0,
            )

    def _write_goal_tasks(self, goal_id_str: str, subgoals: list,
                          today: date) -> list[dict]:
        """将分解结果写入 GoalTask 和 TodoItem 表"""
        created = []
        try:
            from backend.database import SessionLocal
            from backend.models import Goal, GoalTask, TodoItem

            db = SessionLocal()
            try:
                # 取最新 active goal
                latest = db.query(Goal).filter(
                    Goal.status == "active"
                ).order_by(Goal.created_at.desc()).first()
                goal_id = latest.id if latest else None

                for sg in subgoals:
                    for t in sg.get("tasks", []):
                        content = t.get("content", "")
                        category = t.get("category", "其他")
                        daily_quota = self._parse_quota(t.get("daily_quota", ""))

                        if goal_id:
                            gt = GoalTask(
                                goal_id=goal_id,
                                content=f"[{sg['title']}] {content}",
                                category=category,
                                daily_quota=daily_quota,
                            )
                            db.add(gt)

                        todo = TodoItem(
                            date=today,
                            content=f"[{sg['title']}] {content}",
                            category=category,
                            duration_minutes=60,
                            status="pending",
                        )
                        db.add(todo)
                        created.append({"content": content, "category": category})

                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"GoalTask write failed: {e}")

        return created

    def _parse_quota(self, quota_str: str) -> int:
        """解析每日配额字符串为整数"""
        import re
        nums = re.findall(r'\d+', str(quota_str))
        return int(nums[0]) if nums else 0
