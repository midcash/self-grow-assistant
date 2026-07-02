"""预定义发布闸门

- Smoke Gate: 日常开发快速验证, 低阈值
- Release Gate: 发布前完整检查, 高阈值
"""

from backend.agent.evaluation.gates import ReleaseGate, GateCondition

# ── Smoke Gate: 快速验证 ──

SMOKE_GATE = ReleaseGate(
    name="smoke",
    conditions=[
        GateCondition(
            metric="prompt",
            operator=">=",
            threshold=3.0,
            description="Prompt质量: avg_score >= 3.0",
        ),
        GateCondition(
            metric="tool_call",
            operator=">=",
            threshold=3.0,
            description="工具调用: avg_score >= 3.0",
        ),
        GateCondition(
            metric="trajectory",
            operator=">=",
            threshold=3.0,
            description="轨迹路由: avg_score >= 3.0",
        ),
    ],
)

# ── Release Gate: 发布级完整检查 ──

RELEASE_GATE = ReleaseGate(
    name="release",
    conditions=[
        GateCondition(
            metric="prompt",
            operator=">=",
            threshold=4.0,
            description="Prompt质量: avg_score >= 4.0",
        ),
        GateCondition(
            metric="tool_call",
            operator=">=",
            threshold=4.0,
            description="工具调用: avg_score >= 4.0",
        ),
        GateCondition(
            metric="reasoning",
            operator=">=",
            threshold=3.5,
            description="推理质量: avg_score >= 3.5",
        ),
        GateCondition(
            metric="rag",
            operator=">=",
            threshold=3.5,
            description="检索质量: avg_score >= 3.5",
        ),
        GateCondition(
            metric="trajectory",
            operator=">=",
            threshold=3.5,
            description="轨迹路由: avg_score >= 3.5",
        ),
    ],
)

# 预定义闸门列表
DEFAULT_GATES = [SMOKE_GATE, RELEASE_GATE]

# 按名称索引
GATES_BY_NAME = {
    "smoke": SMOKE_GATE,
    "release": RELEASE_GATE,
}
