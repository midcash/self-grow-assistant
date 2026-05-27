"""Searcher Agent — 信息检索 Worker

能力: 搜索、检索、信息聚合
工具: 本地数据库查询、知识库检索、联网搜索(预留)
"""

import asyncio
import logging
from backend.agent.workers.base import WorkerBase, WorkerResult, TaskBrief
from datetime import date

logger = logging.getLogger(__name__)


class SearcherWorker(WorkerBase):
    """信息检索 Agent

    负责搜索和聚合信息:
    - 查询本地数据库 (todo_items, role_models, agent_memory_digests)
    - 检索知识库 (data/agent-memory/wiki/)
    - 联网搜索 (预留 MCP 接口)
    """

    @property
    def role(self) -> str:
        return "searcher"

    @property
    def system_prompt(self) -> str:
        return """你是信息检索专家。负责搜索、查找和聚合用户需要的信息。

你的工作方式:
1. 理解搜索目标
2. 从可用的数据源中检索相关信息
3. 以结构化的方式整理和呈现结果
4. 标注信息来源和可信度

输出要求:
- 用 JSON 格式返回结构化结果
- 包含 "findings" (发现列表) 和 "sources" (来源)
- 如果信息不足，明确说明缺失什么"""

    def capabilities(self) -> list[str]:
        return ["search", "retrieve", "lookup", "research", "find"]

    async def execute(self, brief: TaskBrief) -> WorkerResult:
        """执行检索任务"""
        try:
            findings = []
            sources = []

            # 1. 查询本地数据库
            db_findings = await self._search_local_db(brief)
            if db_findings:
                findings.extend(db_findings)
                sources.append("本地数据库")

            # 2. 查询知识库
            kb_findings = await self._search_knowledge_base(brief)
            if kb_findings:
                findings.extend(kb_findings)
                sources.append("知识库")

            # 3. MCP 外部知识库（本地信息不足时按需调用）
            if self._needs_mcp(brief, len(findings)):
                mcp_findings = await self._search_mcp(brief)
                if mcp_findings:
                    findings.extend(mcp_findings)
                    sources.append("MCP知识库")

            # 4. 如果仍无结果，用 LLM 补充
            if not findings:
                llm_result = await self._llm_supplement(brief)
                findings.append(llm_result)
                sources.append("LLM知识")

            content = self._format_findings(brief.objective, findings, sources)
            return WorkerResult(
                task_id=brief.task_id,
                success=True,
                content=content,
                data={"findings": findings},
                sources=sources,
                confidence=0.8 if sources else 0.5,
            )
        except Exception as e:
            logger.error(f"Searcher failed: {e}")
            return WorkerResult(
                task_id=brief.task_id,
                success=False,
                content=f"检索失败: {e}",
                confidence=0.0,
            )

    async def _search_local_db(self, brief: TaskBrief) -> list[str]:
        """搜索本地 SQLite 数据库"""
        try:
            from backend.database import SessionLocal
            from backend.models import TodoItem, RoleModel, AgentMemoryDigest

            results = []
            db = SessionLocal()
            try:
                # 搜索最近的 TODO
                todos = db.query(TodoItem).order_by(
                    TodoItem.created_at.desc()
                ).limit(20).all()
                if todos:
                    results.append(f"最近日程 ({len(todos)}条): " + "; ".join(
                        f"{t.date}|{t.content}|{t.category}" for t in todos[:10]
                    ))

                # 搜索榜样信息
                models = db.query(RoleModel).filter(RoleModel.is_active == True).all()
                if models:
                    results.append(f"榜样 ({len(models)}位): " + ", ".join(m.name for m in models))

                # 搜索记忆摘要
                today = date.today()
                digest = db.query(AgentMemoryDigest).filter(
                    AgentMemoryDigest.date == today
                ).first()
                if digest and digest.summary:
                    results.append(f"今日摘要: {digest.summary}")
            finally:
                db.close()

            return results
        except Exception as e:
            logger.warning(f"Local DB search failed: {e}")
            return []

    async def _search_knowledge_base(self, brief: TaskBrief) -> list[str]:
        """搜索 Markdown 知识库 (digest/ + wiki/ + domain/)"""
        try:
            from pathlib import Path
            base = Path("data/agent-memory")
            if not base.exists():
                return []

            results = []
            keywords = brief.objective.lower().split()

            # 搜索所有子目录中的 md 文件
            for md_file in list(base.glob("digest/*.md")) + \
                           list(base.glob("wiki/*.md")) + \
                           list(base.glob("domain/**/*.md")):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    # 关键词匹配
                    if any(kw in content.lower() for kw in keywords):
                        # 截取匹配行的上下文
                        results.append(f"记忆[{md_file.stem}]: {content[:300]}")
                except Exception:
                    continue

            # 优先返回最近的记录（digest 文件名含日期）
            return results[:5]
        except Exception as e:
            logger.debug(f"KB search skipped: {e}")
            return []

    async def _llm_supplement(self, brief: TaskBrief) -> str:
        """用 LLM 补充知识"""
        try:
            msg = f"请帮我搜索以下信息: {brief.objective}\n上下文: {brief.context}"
            return await self._call_llm(
                [{"role": "system", "content": "你是信息检索助手，回答简洁准确。"},
                 {"role": "user", "content": msg}],
                max_tokens=1024, temperature=0.3,
            )
        except Exception:
            return f"关于「{brief.objective}」未找到相关信息"

    # ── MCP 外部知识库 ──

    _mcp_config: dict | None = None
    _mcp_session: object | None = None
    _mcp_contexts: tuple | None = None  # (stdio_ctx, session_ctx) for lifetime

    @classmethod
    def load_mcp_config(cls, config: dict) -> None:
        cls._mcp_config = config

    def _needs_mcp(self, brief: TaskBrief, local_hits: int) -> bool:
        """判断是否需要调用外部 MCP 知识库"""
        if not self._mcp_config:
            return False
        # 本地结果不足
        if local_hits < 3:
            return True
        # 任务明确指向外部知识
        mcp_keywords = ["文档", "知识库", "资料", "论文", "笔记", "MCP", "RAG", "搜索", "查找资料"]
        objective = brief.objective + brief.context
        return any(kw in objective for kw in mcp_keywords)

    async def _search_mcp(self, brief: TaskBrief) -> list[str]:
        """通过 MCP 协议查询外部知识库"""
        try:
            session = await self._ensure_mcp_session()
            if session is None:
                return []

            # 调用 query_knowledge_hub
            result = await asyncio.wait_for(
                session.call_tool("query_knowledge_hub", {
                    "query": brief.objective,
                    "top_k": 5,
                }),
                timeout=15.0,
            )

            # 解析 MCP 响应
            texts = []
            for block in getattr(result, "content", []):
                if hasattr(block, "text"):
                    texts.append(block.text)
            return texts[:3] if texts else []

        except asyncio.TimeoutError:
            logger.warning("MCP query timed out (15s)")
            return []
        except Exception as e:
            logger.warning(f"MCP query failed: {e}")
            return []

    async def _ensure_mcp_session(self):
        """懒加载 MCP 子进程 + 会话，保持连接存活"""
        if self._mcp_session is not None:
            return self._mcp_session

        if not self._mcp_config:
            return None

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            server_params = StdioServerParameters(
                command=self._mcp_config.get("command"),
                args=self._mcp_config.get("args", []),
            )

            # 建立 stdio 连接 — 必须持有上下文管理器防止 GC 关闭连接
            self._stdio_ctx = stdio_client(server_params)
            read, write = await asyncio.wait_for(
                self._stdio_ctx.__aenter__(), timeout=10.0,
            )
            self._session_ctx = ClientSession(read, write)
            session = await asyncio.wait_for(
                self._session_ctx.__aenter__(), timeout=10.0,
            )
            await asyncio.wait_for(session.initialize(), timeout=10.0)

            self._mcp_session = session
            logger.info("MCP session established (modular-rag)")
            return session

        except ImportError:
            logger.warning("mcp SDK not installed, MCP search disabled")
            return None
        except Exception as e:
            logger.warning(f"MCP connection failed: {e}")
            return None

    def _format_findings(self, objective: str, findings: list[str],
                         sources: list[str]) -> str:
        parts = [f"## 检索结果: {objective}\n"]
        for i, f in enumerate(findings, 1):
            parts.append(f"{i}. {f}")
        parts.append(f"\n来源: {', '.join(sources)}")
        return "\n".join(parts)
