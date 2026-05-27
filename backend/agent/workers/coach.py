"""Coach Agent — 心理辅导 Worker

基于 CBT（认知行为疗法）框架的结构化辅导。
参考 2026 年 Structure Matters RCT (N=66) 结论: 多 Agent FSM 优于单 Agent。

辅导状态机: 共情倾听 → 识别模式 → 认知重构 → 行动计划 → 复盘
"""

import logging
from backend.agent.workers.base import WorkerBase, WorkerResult, TaskBrief

logger = logging.getLogger(__name__)


class CoachWorker(WorkerBase):
    """心理辅导 Agent

    基于 CBT 框架帮助用户:
    1. 识别自动负性思维 (ANTs)
    2. 检验思维真实性
    3. 替代为建设性思维
    4. 制定行为实验
    """

    @property
    def role(self) -> str:
        return "coach"

    @property
    def system_prompt(self) -> str:
        return """你是一位专业的认知行为疗法(CBT)心理教练。你的目标是帮助用户建立心理韧性。

辅导框架:
1. 共情倾听 — 先理解用户的感受，不要说教
2. 识别模式 — 帮用户发现负性自动思维(ANTs):
   - 灾难化: "这次面试搞砸了，我这辈子完了"
   - 过度泛化: "我总是做不好"
   - 非黑即白: "不做完美就是彻底失败"
   - 读心术: "他们肯定觉得我很蠢"
3. 认知重构 — 用苏格拉底式提问帮用户检验思维:
   - "这个想法有什么证据支持？"
   - "如果朋友有同样的想法，你会怎么对他说？"
   - "最坏的情况真的会发生吗？概率多大？"
4. 行动计划 — 帮用户制定具体的小步骤行为实验
5. 复盘强化 — 帮用户看到自己的进步

原则:
- 不要给建议，用提问引导用户自己发现答案
- 每次只聚焦一个思维模式
- 始终传递希望: 感受是暂时的，能力是积累的
- 用具体例子，不用抽象理论
- 回复以 [ENCOURAGE] 结尾"""

    def capabilities(self) -> list[str]:
        return ["coach", "心理", "辅导", "焦虑", "紧张", "压力", "自卑",
                "害怕", "担心", "鼓励", "安慰", "帮助我"]

    async def execute(self, brief: TaskBrief) -> WorkerResult:
        try:
            user_msg = brief.objective
            context = brief.context

            prompt = (
                f"用户说: {user_msg}\n"
                f"上下文: {context}\n\n"
                f"请根据 CBT 辅导框架回复:\n"
                f"1. 先共情\n"
                f"2. 如果用户表达了负面情绪，识别可能的认知扭曲模式\n"
                f"3. 用提问引导用户重新审视自己的想法\n"
                f"4. 如果需要，提出一个小的行为实验\n"
                f"回复控制在 200 字以内"
            )

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ]

            try:
                reply = await self._call_llm(messages, max_tokens=1024, temperature=0.7)
            except Exception:
                return WorkerResult(
                    task_id=brief.task_id, success=False,
                    content="抱歉，我现在无法提供辅导。请稍后再试。",
                    confidence=0.0,
                )

            return WorkerResult(
                task_id=brief.task_id,
                success=True,
                content=reply,
                sources=["CBT辅导"],
                confidence=0.85,
            )

        except Exception as e:
            logger.error(f"Coach failed: {e}")
            return WorkerResult(
                task_id=brief.task_id, success=False,
                content=f"辅导失败: {e}",
                confidence=0.0,
            )
