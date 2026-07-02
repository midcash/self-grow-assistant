"""GoalDecomposerWorker 评估数据集

评估维度:
- prompt: 系统提示词质量
- reasoning: 目标分解结构正确性/JSON有效性/任务颗粒度
"""

from backend.agent.evaluation.dataset import EvalExample, EvalDataset

# ── Prompt评估 ──

DECOMPOSER_PROMPT_EXAMPLE = EvalExample(
    id="decomposer-prompt-1",
    name="GoalDecomposer系统提示词质量",
    description="评估GoalDecomposerWorker的system_prompt是否包含子目标和每日任务的分解框架",
    worker="goal_decomposer",
    eval_type="prompt",
    rubric="prompt-clarity",
    assertions=[
        {"type": "contains", "value": "子目标"},
        {"type": "contains", "value": "分解"},
        {"type": "contains", "value": "category"},
        {"type": "min_length", "value": 50},
    ],
    tags=["prompt", "smoke"],
)

# ── Reasoning评估 ──

DECOMPOSER_STRUCTURE = EvalExample(
    id="decomposer-reasoning-1",
    name="目标分解结构完整性",
    description="正确分解的目标应包含subgoals数组,每个subgoal有title和tasks",
    worker="goal_decomposer",
    eval_type="reasoning",
    input={
        "task_id": "decompose-test",
        "objective": "在一个月内学会Python编程",
        "context": '{"goal_id": 1}',
    },
    rubric="reasoning-quality",
    assertions=[
        {"type": "json_path", "path": "$.data.subgoals", "not_empty": True},
    ],
    tags=["reasoning", "smoke"],
)

DECOMPOSER_JSON_VALIDITY = EvalExample(
    id="decomposer-reasoning-2",
    name="LLM返回JSON有效性",
    description="LLM应返回符合spec的JSON结构(subgoals数组, 每个含title和tasks)",
    worker="goal_decomposer",
    eval_type="reasoning",
    input={
        "task_id": "decompose-test",
        "objective": "每天阅读30分钟,坚持一个月",
        "context": '{"goal_id": 2}',
    },
    rubric="reasoning-quality",
    tags=["reasoning"],
)

DECOMPOSER_TASK_GRANULARITY = EvalExample(
    id="decomposer-reasoning-3",
    name="任务颗粒度合理性",
    description="分解后的每日任务应该是可执行的(不是过大的子目标)",
    worker="goal_decomposer",
    eval_type="reasoning",
    input={
        "task_id": "decompose-test",
        "objective": "准备技术面试",
        "context": '{"goal_id": 3}',
    },
    rubric="reasoning-quality",
    tags=["reasoning"],
)

DECOMPOSER_NO_GOAL_HANDLING = EvalExample(
    id="decomposer-reasoning-4",
    name="简单目标不分解",
    description="对于简单的目标(如'每天喝水'), LLM可能不生成subgoals, 系统应正确返回空列表",
    worker="goal_decomposer",
    eval_type="reasoning",
    input={
        "task_id": "decompose-test",
        "objective": "每天喝8杯水",
        "context": '{"goal_id": 4}',
    },
    rubric="reasoning-quality",
    assertions=[
        {"type": "json_path", "path": "$.data.subgoals", "not_empty": False},
    ],
    tags=["reasoning"],
)

DECOMPOSER_CATEGORY_CONSTRAINT = EvalExample(
    id="decomposer-reasoning-5",
    name="任务category约束",
    description="所有创建的任务的category必须在规定的7个值中",
    worker="goal_decomposer",
    eval_type="reasoning",
    input={
        "task_id": "decompose-test",
        "objective": "系统学习算法与数据结构",
        "context": '{"goal_id": 5}',
    },
    rubric="reasoning-quality",
    tags=["reasoning"],
)

# ── 聚合 ──

goal_decomposer_dataset = EvalDataset(
    name="goal-decomposer-eval",
    description="GoalDecomposerWorker评估数据集: 含prompt质量/分解结构/JSON有效性/颗粒度",
    examples=[
        DECOMPOSER_PROMPT_EXAMPLE,
        DECOMPOSER_STRUCTURE,
        DECOMPOSER_JSON_VALIDITY,
        DECOMPOSER_TASK_GRANULARITY,
        DECOMPOSER_NO_GOAL_HANDLING,
        DECOMPOSER_CATEGORY_CONSTRAINT,
    ],
)
