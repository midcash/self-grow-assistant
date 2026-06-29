# Architecture Decision Records

> 7 份架构决策记录。每份标注成熟度：🟢 稳定 / 🟡 实验 / 🔴 草稿。

| 序号 | 文档 | 成熟度 | 决策内容 |
|------|------|--------|---------|
| 1 | `api-spec.md` | 🟢 稳定 | REST API 协议（39 端点） |
| 2 | `agent-architecture.md` | 🟢 稳定 | Agent Harness 可插拔架构 + 三层记忆 |
| 3 | `agent-plugin-spec.md` | 🟢 稳定 | 插件契约：LLM/TTS/Priority/Notify 接口 |
| 4 | `multi-agent-architecture.md` | 🟡 实验 | Supervisor-Worker 编排，当前 5 Worker |
| 5 | `mcp-integration-analysis.md` | 🟡 实验 | MCP 外部服务集成（Searcher 侧已通） |
| 6 | `secretary-agent-upgrade.md` | 🟡 实验 | 秘书级升级（Goal/Coach/MotivationEngine） |
| 7 | `goal-achievement-level3-spec.md` | 🔴 草稿 | Level3 长期目标达成闭环升级规格 |
| 8 | `agent-observability-ui-design.md` | 🔴 草稿 | Agent 数据流观测页面设计 (Observe Tab) |

## 架构成熟度总览

```
🟢 稳定层 (3/7): 通信协议 + 插件接口 + API — 不会再大变
🟡 实验层 (3/7): 多Agent编排 + MCP集成 + 自主引擎 — 已知局限，等触发升级
🔴 草稿层 (1/7): Level3 长期目标达成闭环 — 进入实现前需同步 API / 插件合同
```
