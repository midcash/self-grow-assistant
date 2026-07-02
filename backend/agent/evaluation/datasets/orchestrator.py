"""Orchestrator 评估数据集

评估维度:
- trajectory: 计划质量/Worker路由正确性/综合质量
"""

from backend.agent.evaluation.dataset import EvalExample, EvalDataset

# ── Trajectory评估 ──

ORCH_PLAN_QUALITY_SEARCH = EvalExample(
    id="orch-trajectory-1",
    name="计划质量: 搜索类请求",
    description="用户查询信息时, _plan应路由给searcher, 意图为general",
    worker="orchestrator",
    eval_type="trajectory",
    input={
        "user_message": "帮我搜索一下Python教程",
    },
    rubric="trajectory-quality",
    assertions=[
        {"type": "plan_has_worker", "value": "searcher"},
    ],
    tags=["trajectory", "smoke"],
)

ORCH_PLAN_QUALITY_CREATE = EvalExample(
    id="orch-trajectory-2",
    name="计划质量: 创建类请求",
    description="用户要求创建日程时, _plan应路由给executor(SchedulerWorker)",
    worker="orchestrator",
    eval_type="trajectory",
    input={
        "user_message": "帮我安排明天早上9点的跑步任务",
    },
    rubric="trajectory-quality",
    assertions=[
        {"type": "plan_has_worker", "value": "executor"},
    ],
    tags=["trajectory", "smoke"],
)

ORCH_WORKER_ROUTING_DECOMPOSE = EvalExample(
    id="orch-trajectory-3",
    name="Worker路由: 目标分解",
    description="用户提出长期目标时, 应路由给goal_decomposer",
    worker="orchestrator",
    eval_type="trajectory",
    input={
        "user_message": "我想在一个月内学会Python编程,帮我分解一下",
    },
    rubric="trajectory-quality",
    assertions=[
        {"type": "plan_has_worker", "value": "goal_decomposer"},
    ],
    tags=["trajectory"],
)

ORCH_WORKER_ROUTING_COACH = EvalExample(
    id="orch-trajectory-4",
    name="Worker路由: 心理辅导",
    description="用户表达情绪困扰时, 应路由给coach",
    worker="orchestrator",
    eval_type="trajectory",
    input={
        "user_message": "我最近感到非常焦虑和压力大",
    },
    rubric="trajectory-quality",
    assertions=[
        {"type": "plan_has_worker", "value": "coach"},
    ],
    tags=["trajectory"],
)

ORCH_SYNTHESIS_QUALITY = EvalExample(
    id="orch-trajectory-5",
    name="综合质量: 多Worker协作",
    description="复杂请求可能触发多个Worker, 合成结果应连贯统一",
    worker="orchestrator",
    eval_type="trajectory",
    input={
        "user_message": "分析一下我最近的学习习惯,然后帮我规划明天的学习任务",
    },
    rubric="trajectory-quality",
    assertions=[
        {"type": "plan_has_worker", "value": "profiler"},
    ],
    tags=["trajectory"],
)

ORCH_FALLBACK_DIRECT_REPLY = EvalExample(
    id="orch-trajectory-6",
    name="简单请求: 直接回复",
    description="不需要Worker的简单问候应直接回复, 不创建子任务",
    worker="orchestrator",
    eval_type="trajectory",
    input={
        "user_message": "你好",
    },
    rubric="trajectory-quality",
    tags=["trajectory"],
)

# ── 聚合 ──

orchestrator_dataset = EvalDataset(
    name="orchestrator-eval",
    description="Orchestrator评估数据集: 含计划质量/Worker路由/综合质量",
    examples=[
        ORCH_PLAN_QUALITY_SEARCH,
        ORCH_PLAN_QUALITY_CREATE,
        ORCH_WORKER_ROUTING_DECOMPOSE,
        ORCH_WORKER_ROUTING_COACH,
        ORCH_SYNTHESIS_QUALITY,
        ORCH_FALLBACK_DIRECT_REPLY,
    ],
)
