# MCP 集成方案分析 — self-grow 项目

> 成熟度: 🟡 实验阶段 — Searcher 侧 MCP Client 已通。
> 已知局限: Orchestrator 侧 MCP Client 待实现；MCP 工具列表需手动管理。
> 触发升级: 当连接 ≥ 2 个 MCP Server 时，需要统一 MCP Client 管理层。


## 一、MCP 现状（2026 年 5 月）

- 安装量 9700 万+，社区 2000+ MCP Server
- Linux Foundation AAIF 治理（2025 年 12 月起）
- 官方 SDK 持续更新，Streamable HTTP 已取代 SSE

## 二、两种集成模式

### 模式 A：Embedded MCP（推荐）

MCP Server 嵌入现有 FastAPI，同一进程共享服务实例。

```
self-grow/
├── backend/
│   ├── main.py          ← app.mount("/mcp", mcp_app)
│   ├── mcp/             ← 新增: MCP 工具层
│   │   ├── __init__.py
│   │   └── tools.py     ← 把现有服务包装为 MCP tools
│   ├── agent/           ← 已有
│   └── routers/         ← 已有
```

优点：
- 单进程，零 HTTP 开销
- 直接复用现有 Service/Plugin/Database 实例
- 代码量最小（~50 行）

缺点：
- 需要修改 main.py（添加 lifespan + mount）

### 模式 B：Bridge MCP（备选）

独立进程，通过 HTTP 调用现有 REST API。

优点：
- 零修改现有代码

缺点：
- 多进程维护成本
- HTTP 调用额外延迟

**结论：选 Embedded。项目已有 FastAPI，增量最小。**

## 三、技术选型

### 框架：FastMCP

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("self-grow")

@mcp.tool()
async def get_my_tasks(date: str) -> list[dict]:
    """获取指定日期的待办任务。date 格式 YYYY-MM-DD。"""
    # 直接调用现有 todo_service
    ...

@mcp.tool()
async def analyze_my_habits(days: int = 30) -> dict:
    """分析最近 N 天的习惯模式。"""
    ...
```

FastMCP 理由：
- 100k+ 下载量，v3.0（2026.02）已成熟
- 装饰器 API，和 FastAPI 风格一致
- 内置 Streamable HTTP / stdio 双传输

### 传输：Streamable HTTP

- 远程/生产 → Streamable HTTP（`/mcp` 端点）
- 本地调试 → stdio（Claude Desktop 直接连）

## 四、与现有架构的映射

现有 Harness 插件 → MCP Tool 的自然映射：

| 现有能力 | MCP Tool | 输入 | 输出 |
|---------|----------|------|------|
| Searcher._search_local_db | `search_my_data` | query: str | 本地数据摘要 |
| Profiler._analyze_completion | `get_my_profile` | days: int | 用户画像 JSON |
| SchedulerWorker._create_todos | `add_schedule` | tasks: list | 创建结果 |
| PriorityEngine.evaluate | `evaluate_priorities` | date: str | 优先级排序 |
| LLMAdapter.chat | （不暴露，Agent 内部使用） | — | — |
| TTS | （不暴露，表现层） | — | — |

## 五、外部 Agent 接入场景

### 场景 1：Claude Desktop 直连

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "self-grow": {
      "command": "python",
      "args": ["backend/mcp/server.py"],
      "env": { "SELFGROW_DATA_DIR": "..." }
    }
  }
}
```

Claude Desktop 可以通过 MCP 直接查询你的日程、分析习惯、添加任务。

### 场景 2：本地 Agent 当作 MCP Client

```python
# 项目自己的 Orchestrator 也可以作为 MCP Client
# 调用外部 MCP Server（搜索、日历、邮件等）
from mcp import ClientSession, StdioServerParameters

async def call_external_mcp(server_cmd: str, tool: str, args: dict):
    ...

# Orchestrator 增强：Searcher 可联网搜索
# Executor 可写入外部日历
```

### 场景 3：暴露给其他开发者/应用

`/mcp` 端点是标准协议，任何 MCP 兼容客户端都能用。

## 六、实施路线

| Phase | 内容 | 文件数 |
|-------|------|--------|
| **P0** 安装依赖 | `pip install mcp` (官方 SDK) | 0 |
| **P1** 创建 MCP 工具 | `backend/mcp/tools.py` — 5 个 tool | 1 |
| **P2** 嵌入 FastAPI | `main.py` 加 lifespan + mount | 修改 1 |
| **P3** stdio 入口 | `backend/mcp/server.py` — 供 Claude Desktop | 1 |
| **P4** MCP Client | Orchestrator 可调外部 MCP Server | 修改 1 |
|| **总计** | **3 新 + 2 改** |

## 七、暂不推荐的事项

- 不引入 LangChain MCP Adapter（太重，项目已有自己的 Agent 框架）
- 不引入 smolagents（同上）
- 不引入 Kafka/Flink（个人助手不需要流处理）

## 八、预期收益

1. **互操作**：你的日程数据可被 Claude Desktop、Codex 等任何 MCP 客户端访问
2. **Agent 能力扩展**：Orchestrator 可调用外部 MCP Server（联网搜索、日历、邮件）
3. **标准化**：工具接口符合行业标准，方便后续扩展和社区工具复用
4. **解耦**：把"提供工具"和"使用工具"分开，Orchestrator 不关心工具实现细节
