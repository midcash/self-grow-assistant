"""CoachWorker 评估数据集

评估维度:
- prompt: 系统提示词质量(CBT框架完整性)
- reasoning: CBT状态机遵循度/共情检测/行动计划质量
"""

from backend.agent.evaluation.dataset import EvalExample, EvalDataset

# ── Prompt评估 ──

COACH_PROMPT_EXAMPLE = EvalExample(
    id="coach-prompt-1",
    name="Coach系统提示词质量",
    description="评估CoachWorker的CBT system_prompt是否包含五步辅导框架和关键原则",
    worker="coach",
    eval_type="prompt",
    rubric="prompt-clarity",
    assertions=[
        {"type": "contains", "value": "共情倾听"},
        {"type": "contains", "value": "识别模式"},
        {"type": "contains", "value": "认知重构"},
        {"type": "contains", "value": "行动计划"},
        {"type": "contains", "value": "复盘强化"},
        {"type": "contains", "value": "CBT"},
        {"type": "min_length", "value": 100},
    ],
    tags=["prompt", "smoke"],
)

# ── Reasoning评估 ──

COACH_EMPATHY_DETECTION = EvalExample(
    id="coach-reasoning-1",
    name="CBT共情倾听",
    description="Coach应先理解用户感受, 用温暖的语气回应, 不直接给建议",
    worker="coach",
    eval_type="reasoning",
    input={
        "task_id": "coach-test",
        "objective": "我今天面试失败了,感觉非常沮丧和自卑",
    },
    rubric="reasoning-quality",
    tags=["reasoning", "smoke"],
)

COACH_ANT_PATTERN_ID = EvalExample(
    id="coach-reasoning-2",
    name="CBT负性自动思维识别",
    description="Coach应能识别并命名用户的认知扭曲模式(灾难化/过度泛化/非黑即白等)",
    worker="coach",
    eval_type="reasoning",
    input={
        "task_id": "coach-test",
        "objective": "我总是做不好任何事情,这次考试又没及格,我这辈子完了",
    },
    rubric="reasoning-quality",
    tags=["reasoning"],
)

COACH_SOCRATIC_QUESTIONING = EvalExample(
    id="coach-reasoning-3",
    name="CBT苏格拉底式提问",
    description="Coach应用提问而非说教来引导用户, 使用'证据/朋友/概率'等检验方法",
    worker="coach",
    eval_type="reasoning",
    input={
        "task_id": "coach-test",
        "objective": "我感到非常焦虑,因为明天的演讲我觉得自己一定会搞砸",
    },
    rubric="reasoning-quality",
    tags=["reasoning"],
)

COACH_ACTION_PLAN = EvalExample(
    id="coach-reasoning-4",
    name="CBT行动计划制定",
    description="Coach应在辅导后期帮用户制定具体可执行的行为实验",
    worker="coach",
    eval_type="reasoning",
    input={
        "task_id": "coach-test",
        "objective": "我最近一直拖延,工作效率很低,想改变",
    },
    rubric="reasoning-quality",
    tags=["reasoning"],
)

COACH_NO_ADVICE_PRINCIPLE = EvalExample(
    id="coach-reasoning-5",
    name="不给建议原则",
    description="Coach应遵守'不给建议,用提问引导'的原则, 不应直接给出解决方案",
    worker="coach",
    eval_type="reasoning",
    input={
        "task_id": "coach-test",
        "objective": "我最近和朋友发生了矛盾,不知道该怎么办",
    },
    rubric="reasoning-quality",
    tags=["reasoning"],
)

COACH_ENCOURAGE_ENDING = EvalExample(
    id="coach-reasoning-6",
    name="积极结尾标记",
    description="Coach的回复应以鼓励性话语结尾, 传递希望和力量感",
    worker="coach",
    eval_type="reasoning",
    input={
        "task_id": "coach-test",
        "objective": "我对自己很失望,觉得没有进步",
    },
    rubric="reasoning-quality",
    tags=["reasoning"],
)

# ── 聚合 ──

coach_dataset = EvalDataset(
    name="coach-eval",
    description="CoachWorker评估数据集: 含CBT框架完整性/共情/思维识别/提问/行动计划",
    examples=[
        COACH_PROMPT_EXAMPLE,
        COACH_EMPATHY_DETECTION,
        COACH_ANT_PATTERN_ID,
        COACH_SOCRATIC_QUESTIONING,
        COACH_ACTION_PLAN,
        COACH_NO_ADVICE_PRINCIPLE,
        COACH_ENCOURAGE_ENDING,
    ],
)
