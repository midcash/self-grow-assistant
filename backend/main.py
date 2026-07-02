import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import engine, Base
from backend.routers import qualities, todos, progress, reports, role_models, dashboard_bg, agent, evaluation
from backend.utils import get_static_dir, get_data_dir
from backend.agent.config import ConfigLoader


def is_dev():
    if getattr(sys, 'frozen', False):
        return False
    return os.getenv("SELFGROW_ENV", "dev") == "dev"


def init_database():
    Base.metadata.create_all(bind=engine)
    _migrate()
    _ensure_seed_images()


def _migrate():
    """Safe migration: add columns that may be missing in existing databases."""
    import sqlite3
    from backend.database import DATA_DIR
    db_path = os.path.join(DATA_DIR, "self-grow.db")
    if not os.path.exists(db_path):
        return
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # v1.2.1: add image_url to role_models
        cursor.execute("PRAGMA table_info(role_models)")
        columns = [row[1] for row in cursor.fetchall()]
        if "image_url" not in columns:
            cursor.execute("ALTER TABLE role_models ADD COLUMN image_url VARCHAR(500) DEFAULT ''")
            conn.commit()

        # Update existing role_models with seed image URLs if empty
        seed_images = {
            "沈腾": "/api/v1/static/images/role_models/shenteng.png",
            "马天宇": "/api/v1/static/images/role_models/matianyu.png",
            "王安宇": "/api/v1/static/images/role_models/wanganyu.png",
            "陈瑶": "/api/v1/static/images/role_models/chenyao.png",
            "黄灿灿": "/api/v1/static/images/role_models/huangcancan.png",
            "易烊千玺": "/api/v1/static/images/role_models/yiyangqianxi.png",
            "游本昌": "/api/v1/static/images/role_models/youbenchang.png",
            "辛芷蕾": "/api/v1/static/images/role_models/xinzhilei.png",
            "全红婵": "/api/v1/static/images/role_models/quanhongchan.png",
            "刘宇宁": "/api/v1/static/images/role_models/liuyuning.png",
            "曹骏": "/api/v1/static/images/role_models/caojun.png",
            "舒淇": "/api/v1/static/images/role_models/shuqi.png",
        }
        for name, url in seed_images.items():
            cursor.execute(
                "UPDATE role_models SET image_url = ? WHERE name = ? AND (image_url = '' OR image_url IS NULL)",
                (url, name),
            )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _ensure_seed_images():
    """In frozen mode, copy bundled seed images to the writable data directory."""
    import shutil
    if not getattr(sys, 'frozen', False):
        return
    dest_dir = os.path.join(get_data_dir(), "images", "role_models")
    if os.path.isdir(dest_dir) and os.listdir(dest_dir):
        return
    os.makedirs(dest_dir, exist_ok=True)
    src_dir = os.path.join(sys._MEIPASS, "data", "images", "role_models")
    if os.path.isdir(src_dir):
        for f in os.listdir(src_dir):
            fp = os.path.join(src_dir, f)
            if os.path.isfile(fp):
                shutil.copy2(fp, os.path.join(dest_dir, f))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    await _init_agent()
    yield
    await _shutdown_agent()


def _load_agent_config():
    """加载智能体配置"""
    import os as _os
    config_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "agent-config.yaml")
    if _os.path.exists(config_path):
        return ConfigLoader.load(config_path)
    return ConfigLoader.get_default_config()


async def _init_agent():
    """初始化 Agent Harness 和插件"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        from backend.agent.harness import AgentHarness
        from backend.agent.plugins.llm_adapter.factory import LLMFactory
        from backend.agent.plugins.tts_engine.factory import TTSFactory
        from backend.agent.plugins.priority_engine.factory import PriorityFactory
        from backend.agent.plugins.notifier.factory import NotifierFactory
        from backend.agent.scheduler import AgentScheduler

        config = _load_agent_config()
        harness = AgentHarness()
        await harness.start(config)

        plugin_cfg = config.get("plugins", {})

        # 1. 加载 LLM 插件
        llm_cfg = plugin_cfg.get("llm", {})
        llm_default = llm_cfg.get("default", "deepseek")
        llm_plugin = LLMFactory.create(llm_default)
        await llm_plugin.on_load(llm_cfg.get(llm_default, {}))
        harness.registry._plugins["llm"] = llm_plugin
        harness.registry._manifests["llm"] = llm_plugin.manifest
        logger.info(f"LLM plugin loaded: {llm_plugin.manifest.name}")

        # 2. 加载 TTS 插件
        tts_cfg = plugin_cfg.get("tts", {})
        tts_default = tts_cfg.get("default", "qwen")
        tts_plugin = TTSFactory.create(tts_default)
        await tts_plugin.on_load(tts_cfg.get(tts_default, {}))
        harness.registry._plugins["tts"] = tts_plugin
        harness.registry._manifests["tts"] = tts_plugin.manifest
        logger.info(f"TTS plugin loaded: {tts_plugin.manifest.name}")

        # 3. 加载优先级引擎
        priority_cfg = plugin_cfg.get("priority", {})
        priority_plugin = PriorityFactory.create(priority_cfg.get("engine", "weighted"))
        await priority_plugin.on_load(priority_cfg)
        harness.registry._plugins["priority"] = priority_plugin
        harness.registry._manifests["priority"] = priority_plugin.manifest
        logger.info(f"Priority engine loaded: {priority_plugin.manifest.name}")

        # 4. 加载通知插件
        notify_cfg = plugin_cfg.get("notify", {})
        notify_default = notify_cfg.get("default", "voice")
        notify_plugin = NotifierFactory.create(notify_default)
        await notify_plugin.on_load(notify_cfg.get(notify_default, {}))
        harness.registry._plugins["notify"] = notify_plugin
        harness.registry._manifests["notify"] = notify_plugin.manifest
        # 注入 TTS 引用到 voice alert
        notify_plugin._config["_tts_plugin"] = tts_plugin
        logger.info(f"Notifier loaded: {notify_plugin.manifest.name}")

        # 5. 初始化调度器
        cron_expr = config.get("agent", {}).get("cron", "*/20 * * * *")
        harness._scheduler = AgentScheduler(cron_expr)

        # 6. 定义评估回调
        async def evaluate_and_notify():
            from backend.database import SessionLocal
            from datetime import date
            from backend.models import TodoItem, AgentTaskPriority
            from backend.agent.plugins.notifier.base import Alert

            db = SessionLocal()
            try:
                today = date.today()
                pending = (
                    db.query(TodoItem)
                    .filter(TodoItem.date == today, TodoItem.status == "pending")
                    .all()
                )
                if not pending:
                    return

                default_imp = priority_cfg.get("default_importance", 8)
                tasks = [{"id": t.id, "content": t.content, "category": t.category, "importance": default_imp} for t in pending]
                context = {"current_time": str(today), "_harness": harness}
                scored = await priority_plugin.evaluate(tasks, context)

                for s in scored:
                    record = AgentTaskPriority(
                        todo_id=s.todo_id,
                        urgency_score=s.urgency_score,
                        importance_score=s.importance_score,
                        algorithm_score=s.algorithm_score,
                        llm_score=s.llm_score,
                        final_score=s.priority_score,
                        llm_reasoning=s.llm_reasoning,
                        suggested_action=s.suggested_action,
                    )
                    db.add(record)
                db.commit()

                # 发送通知
                for s in scored:
                    if priority_plugin.needs_alert(s):
                        await notify_plugin.notify(Alert(
                            title="任务提醒",
                            message=f"{s.content} - {s.suggested_action or '建议立即处理'}",
                            level="urgent" if s.priority_score > 0.8 else "normal",
                            task_id=s.todo_id,
                        ))
            except Exception as e:
                logger.error(f"Scheduled evaluation error: {e}")
            finally:
                db.close()

            # MotivationEngine: 扫描 Goal 压力，自主提醒
            try:
                from backend.agent.motivation_engine import MotivationEngine
                engine = MotivationEngine()
                await engine.tick(notify_plugin, tts_plugin)
            except Exception as e:
                logger.error(f"MotivationEngine error: {e}")

        harness._evaluate_and_notify = evaluate_and_notify
        harness._scheduler.start(evaluate_and_notify)
        logger.info(f"Agent scheduler + MotivationEngine started: {cron_expr}")

        # 6. 加载 MCP 配置（注入 Searcher，按需连接外部知识库）
        mcp_cfg = config.get("mcp_servers", [])
        if mcp_cfg:
            from backend.agent.workers.searcher import SearcherWorker
            SearcherWorker.load_mcp_config(mcp_cfg[0])
            logger.info(f"MCP server config loaded: {mcp_cfg[0].get('name')}")

        # 7. 初始化多 Agent 编排器
        from backend.agent.orchestrator import Orchestrator
        orchestrator = Orchestrator(llm_plugin)
        await orchestrator.warmup()
        agent.set_orchestrator(orchestrator)
        logger.info("Multi-Agent Orchestrator initialized")

        # 注册到 agent 路由
        agent.set_harness(harness)
        logger.info("Agent Harness fully initialized")

    except Exception as e:
        logger.error(f"Agent initialization failed: {e}")


async def _shutdown_agent():
    """关闭 Agent Harness"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        from backend.routers.agent import _harness
        if _harness:
            if hasattr(_harness, '_scheduler'):
                _harness._scheduler.stop()
            await _harness.shutdown()
            logger.info("Agent Harness shut down")
    except Exception as e:
        logger.error(f"Agent shutdown error: {e}")


app = FastAPI(
    title="Self-Grow API",
    description="自我成长可视化系统后端",
    version="1.0.0",
    lifespan=lifespan,
)

if is_dev():
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# API routes registered first
app.include_router(qualities.router)
app.include_router(todos.router)
app.include_router(progress.router)
app.include_router(reports.router)
app.include_router(role_models.router)
app.include_router(dashboard_bg.router)
app.include_router(agent.router)
app.include_router(evaluation.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Mount uploaded images directory (user uploads + seed images)
IMAGES_DIR = get_data_dir() / "images"
if not IMAGES_DIR.exists():
    os.makedirs(IMAGES_DIR, exist_ok=True)
app.mount("/api/v1/static/images", StaticFiles(directory=str(IMAGES_DIR)), name="uploaded_images")


# In production, serve static files (must be last to not override API routes)
STATIC_DIR = get_static_dir()
if STATIC_DIR.exists() and not is_dev():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str = ""):
        target = STATIC_DIR / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=is_dev())
