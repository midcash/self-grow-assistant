"""SearcherWorker 评估数据集

评估维度:
- prompt: 系统提示词质量(clarity + completeness + actionability)
- tool_call: MCP决策正确性(local insufficient触发/关键词触发/sufficient跳过)
- rag: 检索质量(source attribution + hallucination check)
"""

from backend.agent.evaluation.dataset import EvalExample, EvalDataset

# ── Prompt评估 ──

SEARCHER_PROMPT_EXAMPLE = EvalExample(
    id="searcher-prompt-1",
    name="Searcher系统提示词质量",
    description="评估SearcherWorker的system_prompt是否清晰定义了搜索步骤、来源标注和输出格式",
    worker="searcher",
    eval_type="prompt",
    rubric="prompt-clarity",
    assertions=[
        {"type": "contains", "value": "搜索"},
        {"type": "contains", "value": "来源"},
        {"type": "contains", "value": "JSON"},
        {"type": "min_length", "value": 50},
    ],
    tags=["prompt", "smoke"],
)

# ── Tool Call评估 ──

SEARCHER_TOOL_MCP_TRIGGER_LOCAL_INSUFFICIENT = EvalExample(
    id="searcher-tool-1",
    name="MCP触发: 本地结果不足",
    description="当本地搜索结果<3条时, 应触发MCP外部搜索",
    worker="searcher",
    eval_type="tool_call",
    input={
        "type": "mcp_decision",
        "local_hits": 1,
        "objective": "搜索知识库文档",
    },
    expected_output={"needs_mcp": True},
    assertions=[
        {"type": "equals", "path": "needs_mcp", "value": True},
    ],
    tags=["tool_call", "mcp", "smoke"],
)

SEARCHER_TOOL_MCP_TRIGGER_KEYWORD = EvalExample(
    id="searcher-tool-2",
    name="MCP触发: 关键词匹配",
    description="当查询包含'搜索'/MCP关键词时, 即使本地结果充足也触发MCP",
    worker="searcher",
    eval_type="tool_call",
    input={
        "type": "mcp_decision",
        "local_hits": 10,
        "objective": "搜索知识库中的最新文档",
    },
    expected_output={"needs_mcp": True},
    assertions=[
        {"type": "equals", "path": "needs_mcp", "value": True},
    ],
    tags=["tool_call", "mcp"],
)

SEARCHER_TOOL_MCP_SKIP_SUFFICIENT = EvalExample(
    id="searcher-tool-3",
    name="MCP跳过: 本地结果充足",
    description="当本地结果>=3条且无MCP关键词时, 跳过MCP调用",
    worker="searcher",
    eval_type="tool_call",
    input={
        "type": "mcp_decision",
        "local_hits": 5,
        "objective": "查一下最近的记录",
    },
    expected_output={"needs_mcp": False},
    assertions=[
        {"type": "equals", "path": "needs_mcp", "value": False},
    ],
    tags=["tool_call", "mcp", "smoke"],
)

SEARCHER_TOOL_MCP_NO_CONFIG = EvalExample(
    id="searcher-tool-4",
    name="MCP未配置: 不触发",
    description="当MCP config为空时, 所有查询都不触发MCP",
    worker="searcher",
    eval_type="tool_call",
    input={
        "type": "mcp_decision",
        "local_hits": 0,
        "objective": "搜索知识库",
    },
    expected_output={"needs_mcp": False},
    assertions=[
        {"type": "equals", "path": "needs_mcp", "value": False},
    ],
    tags=["tool_call", "mcp"],
)

# ── RAG评估 ──

SEARCHER_RAG_SOURCE_ATTRIBUTION = EvalExample(
    id="searcher-rag-1",
    name="检索来源标注",
    description="搜索结果应包含明确的来源(sources列表不为空)",
    worker="searcher",
    eval_type="rag",
    input={
        "task_id": "search-test",
        "objective": "查找Python相关教程",
    },
    rubric="retrieval-quality",
    assertions=[
        {"type": "json_path", "path": "$.data.findings", "not_empty": True},
    ],
    tags=["rag", "smoke"],
)

SEARCHER_RAG_HALLUCINATION_CHECK = EvalExample(
    id="searcher-rag-2",
    name="检索幻觉检测",
    description="当本地和MCP均无结果时, 应明确说明信息不足而不编造",
    worker="searcher",
    eval_type="rag",
    input={
        "task_id": "search-test",
        "objective": "查找不存在的XYZ资料",
    },
    rubric="retrieval-quality",
    assertions=[
        {"type": "not_contains", "value": "找到了"},  # 不应声称找到了
    ],
    tags=["rag"],
)

# ── 聚合为Dataset ──

searcher_dataset = EvalDataset(
    name="searcher-eval",
    description="SearcherWorker评估数据集: 含prompt质量/tool calling/RAG评估",
    examples=[
        SEARCHER_PROMPT_EXAMPLE,
        SEARCHER_TOOL_MCP_TRIGGER_LOCAL_INSUFFICIENT,
        SEARCHER_TOOL_MCP_TRIGGER_KEYWORD,
        SEARCHER_TOOL_MCP_SKIP_SUFFICIENT,
        SEARCHER_TOOL_MCP_NO_CONFIG,
        SEARCHER_RAG_SOURCE_ATTRIBUTION,
        SEARCHER_RAG_HALLUCINATION_CHECK,
    ],
)
