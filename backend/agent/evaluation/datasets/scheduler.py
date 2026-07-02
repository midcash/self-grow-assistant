"""SchedulerWorker 评估数据集

评估维度:
- prompt: 系统提示词质量
- tool_call: 任务解析正确性 + DB写入正确性
"""

from backend.agent.evaluation.dataset import EvalExample, EvalDataset

# ── Prompt评估 ──

SCHEDULER_PROMPT_EXAMPLE = EvalExample(
    id="scheduler-prompt-1",
    name="Scheduler系统提示词质量",
    description="评估SchedulerWorker的system_prompt是否包含日程创建的关键步骤和category约束",
    worker="executor",
    eval_type="prompt",
    rubric="prompt-clarity",
    assertions=[
        {"type": "contains", "value": "日程"},
        {"type": "contains", "value": "日期"},
        {"type": "contains", "value": "学习/运动/工作/生活/阅读/冥想/其他"},
        {"type": "min_length", "value": 50},
    ],
    tags=["prompt", "smoke"],
)

# ── Tool Call评估 ──

SCHEDULER_TASK_PARSE_STRUCTURED = EvalExample(
    id="scheduler-tool-1",
    name="结构化输入直接解析",
    description="当context中包含结构化tasks数据时, 直接使用而不调用LLM",
    worker="executor",
    eval_type="tool_call",
    input={
        "task_id": "scheduler-test",
        "objective": "创建日程",
        "context": {"tasks": [{"date": "2026-07-03", "content": "学习Python", "category": "学习", "duration_minutes": 60}]},
    },
    assertions=[
        {"type": "equals", "path": "success", "value": True},
    ],
    tags=["tool_call", "smoke"],
)

SCHEDULER_TASK_CATEGORY_VALID = EvalExample(
    id="scheduler-tool-2",
    name="Category合法性检查",
    description="创建的任务category必须在规定的7个值中",
    worker="executor",
    eval_type="tool_call",
    input={
        "task_id": "scheduler-test",
        "objective": "创建运动任务",
        "context": {"tasks": [{"date": "2026-07-03", "content": "跑步", "category": "运动", "duration_minutes": 30}]},
    },
    assertions=[
        {"type": "equals", "path": "success", "value": True},
    ],
    tags=["tool_call"],
)

SCHEDULER_NO_TASKS_HANDLING = EvalExample(
    id="scheduler-tool-3",
    name="无任务时的处理",
    description="当输入中没有任何可创建的任务时, 应明确返回success=False",
    worker="executor",
    eval_type="tool_call",
    input={
        "task_id": "scheduler-test",
        "objective": "创建日程",
        "context": {},
    },
    # 无structured tasks且无LLM时返回false
    tags=["tool_call"],
)

SCHEDULER_MULTI_TASK_CREATION = EvalExample(
    id="scheduler-tool-4",
    name="多任务批量创建",
    description="一次创建多个日程条目时, 应全部成功",
    worker="executor",
    eval_type="tool_call",
    input={
        "task_id": "scheduler-test",
        "objective": "批量创建日程",
        "context": {"tasks": [
            {"date": "2026-07-03", "content": "学习", "category": "学习", "duration_minutes": 60},
            {"date": "2026-07-03", "content": "跑步", "category": "运动", "duration_minutes": 30},
            {"date": "2026-07-04", "content": "读书", "category": "阅读", "duration_minutes": 45},
        ]},
    },
    assertions=[
        {"type": "equals", "path": "success", "value": True},
    ],
    tags=["tool_call"],
)

# ── 聚合 ──

scheduler_dataset = EvalDataset(
    name="scheduler-eval",
    description="SchedulerWorker评估数据集: 含prompt质量/任务解析/批量创建",
    examples=[
        SCHEDULER_PROMPT_EXAMPLE,
        SCHEDULER_TASK_PARSE_STRUCTURED,
        SCHEDULER_TASK_CATEGORY_VALID,
        SCHEDULER_NO_TASKS_HANDLING,
        SCHEDULER_MULTI_TASK_CREATION,
    ],
)
