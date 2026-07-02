"""ProfilerWorker 评估数据集

评估维度:
- prompt: 系统提示词质量
- reasoning: 用户画像分析正确性(数据结构完整性)
"""

from backend.agent.evaluation.dataset import EvalExample, EvalDataset

# ── Prompt评估 ──

PROFILER_PROMPT_EXAMPLE = EvalExample(
    id="profiler-prompt-1",
    name="Profiler系统提示词质量",
    description="评估ProfilerWorker的system_prompt是否包含用户画像分析的关键要素",
    worker="profiler",
    eval_type="prompt",
    rubric="prompt-clarity",
    assertions=[
        {"type": "contains", "value": "画像"},
        {"type": "contains", "value": "偏好"},
        {"type": "contains", "value": "数据"},
        {"type": "min_length", "value": 50},
    ],
    tags=["prompt", "smoke"],
)

# ── Reasoning评估 ──

PROFILER_DATA_COMPLETENESS = EvalExample(
    id="profiler-reasoning-1",
    name="画像分析数据完整性",
    description="Profiler的输出应包含completion_patterns/qualities/categories/recent_context/goal_gaps五个字段",
    worker="profiler",
    eval_type="reasoning",
    input={
        "task_id": "profile-test",
        "objective": "分析用户最近的完成模式和行为偏好",
    },
    rubric="reasoning-quality",
    assertions=[
        {"type": "json_path", "path": "$.data.profile_data", "not_empty": True},
    ],
    tags=["reasoning"],
)

PROFILER_GOAL_GAP_ACCURACY = EvalExample(
    id="profiler-reasoning-2",
    name="目标差距分析正确性",
    description="当目标进度严重落后时, gap_ratio应正确反映差距",
    worker="profiler",
    eval_type="reasoning",
    input={
        "task_id": "profile-test",
        "objective": "分析用户目标完成差距",
    },
    rubric="reasoning-quality",
    assertions=[
        {"type": "json_path", "path": "$.data.profile_data.goal_gaps", "not_empty": True},
    ],
    tags=["reasoning"],
)

PROFILER_CATEGORY_TOP3 = EvalExample(
    id="profiler-reasoning-3",
    name="用户分类偏好Top3分析",
    description="Profiler应能返回用户最常投入时间的Top3分类",
    worker="profiler",
    eval_type="reasoning",
    input={
        "task_id": "profile-test",
        "objective": "查看用户偏好分类",
    },
    rubric="reasoning-quality",
    assertions=[
        {"type": "json_path", "path": "$.data.profile_data.categories", "not_empty": True},
    ],
    tags=["reasoning"],
)

PROFILER_RECENT_CONTEXT = EvalExample(
    id="profiler-reasoning-4",
    name="近期上下文分析",
    description="Profiler应能从AgentMemoryDigest中提取近期关键上下文",
    worker="profiler",
    eval_type="reasoning",
    input={
        "task_id": "profile-test",
        "objective": "分析最近的用户记录",
    },
    rubric="reasoning-quality",
    tags=["reasoning"],
)

# ── 聚合 ──

profiler_dataset = EvalDataset(
    name="profiler-eval",
    description="ProfilerWorker评估数据集: 含prompt质量/推理正确性",
    examples=[
        PROFILER_PROMPT_EXAMPLE,
        PROFILER_DATA_COMPLETENESS,
        PROFILER_GOAL_GAP_ACCURACY,
        PROFILER_CATEGORY_TOP3,
        PROFILER_RECENT_CONTEXT,
    ],
)
