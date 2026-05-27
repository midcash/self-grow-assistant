# self-grow — 自我成长可视化系统

## 开发约束（SDD — Specification-Driven Development）

> 2026 年行业共识：规范纪律是 AI 辅助开发的唯一约束条件，不是模型能力。
> 五条约束，每条都基于可论证的工程实践。

### 1. Spec-First 原则（规范先行）

任何新功能开发前，必须在 `contracts/` 下回答三个问题：
- 这个功能要解决什么问题？（需求描述）
- 它会改变哪些已有的接口/协议？（影响面分析）
- 成功标准是什么？（怎么验证完成）

禁止在未回答这三个问题的情况下直接写代码。

### 2. 契约不可破坏（Contract Integrity）

`TaskBrief`（8 字段）和 `WorkerResult`（6 字段）定义在 `backend/agent/workers/base.py`。
这是整个系统的唯一通信协议。
- 新增 Worker → 实现协议即可，不修改协议
- 修改协议 → 先更新 `contracts/agent-plugin-spec.md` → 再改 `base.py` → 最后改所有 Worker
- 任何改动必须通过 `tests/test_workers.py` 中的协议测试

### 3. 架构决策可追溯（ADR）

每次做出架构决策，在 `contracts/` 下记录，包含：
- 决策日期和触发背景
- 考虑了哪些选项
- 为什么选这个方案的论证
- 后果（什么被简化了，什么被复杂化了）

已有 ADR：`agent-architecture.md` / `multi-agent-architecture.md` / `mcp-integration-analysis.md` / `secretary-agent-upgrade.md`

### 4. 变更透明（Change Transparency）

修改已有模块前，必须说明：
1. 当前是怎么做的（引用具体代码行）
2. 为什么需要改（触发原因）
3. 改动对现有调用方的影响（谁依赖这个模块）

禁止在未说明"原状-原因-影响面"的情况下直接替换实现方式。

### 5. 质量门禁（Quality Gate）

每次开发完成后必须通过：
```bash
venv/Scripts/python -m pytest tests/ -v  # 15 个测试必须全过
cd frontend && npm run build              # 构建必须成功
```

两项均通过后才算一个可提交的增量。

---

## 项目定位
帮助用户将抽象的个人品质目标转化为可量化的日常 TODO 指标，通过可视化图表追踪成长轨迹。
核心理念：从"仰望明星的闪光点"到"让自己也具备闪光点"。

## 技术栈
- 后端: Python 3.12+ / FastAPI / SQLAlchemy / SQLite
- 前端: Vue 3 / Vite / ECharts / Tailwind CSS
- 打包: PyInstaller → `./dist/Self-Grow.exe`（唯一打包产物，禁止复制到根目录）
- 环境: Python venv（在项目根目录创建 `venv/`）
- 开发启动: `venv/Scripts/python run.py`（启动 FastAPI + 原生窗口）
- 仅后端: `venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload`
- 仅前端: `cd frontend && npm run dev`（Vite 开发服务器，端口 5173，自动代理 API 到 8000）

## 目录结构
```
self-grow/
├── backend/           ← 后端 Agent 专属，前端 Agent 禁止修改
│   ├── main.py        ← FastAPI 入口，同时 serve 静态文件
│   ├── models.py      ← SQLAlchemy 模型
│   ├── database.py    ← 数据库连接和初始化
│   ├── routers/       ← 各模块路由
│   ├── services/      ← 业务逻辑层
│   └── requirements.txt
├── frontend/          ← 前端 Agent 专属，后端 Agent 禁止修改
│   ├── src/
│   │   ├── App.vue
│   │   ├── views/     ← 页面组件
│   │   ├── components/← 通用组件
│   │   └── api/       ← 后端 API 调用封装
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── contracts/         ← 共享合同，Team Lead 编写，双方 Agent 只读
│   └── api-spec.md    ← API 接口协议
├── static/            ← 前端构建产物，npm run build 后输出到这里
├── dist/              ← PyInstaller 打包输出，Self-Grow.exe 唯一位置
│   └── data/          ← exe 模式用户数据（数据库 + 上传图片），禁止删除
├── data/              ← 开发模式用户数据（数据库 + 图片），禁止删除
│   ├── self-grow.db   ← SQLite 数据库
│   └── images/        ← 用户上传的图片 + 种子图片
├── build/             ← PyInstaller 构建临时目录，可安全删除
├── .claude/
│   ├── settings.json  ← Claude Code 配置
│   └── skills/        ← Agent Skills
├── CLAUDE.md          ← 本文件
└── venv/              ← Python 虚拟环境（gitignore）
```

## 开发约定
1. 后端 Agent 和前端 Agent 通过 `contracts/api-spec.md` 对齐接口，不得直接沟通修改
2. 数据模型以 `backend/models.py` 为唯一真源，前端类型手动对齐（不引入 OpenAPI 生成）
3. 所有变更必须先更新对应 Skill 文件或 API 合同，再写代码
4. 每次提交前必须验证：后端 pytest 通过 + 前端 vite build 通过

## Sprint 流程
1. Team Lead 更新 `contracts/api-spec.md`
2. Team Lead 分配后端任务 → Backend Agent 实现 + 自测
3. Backend Agent 完成后通知 → Team Lead 验证 API
4. Team Lead 分配前端任务 → Frontend Agent 实现 + 自测
5. Team Lead 集成测试

## 禁止事项
- 禁止不经过 Team Lead 直接修改对方的文件
- 禁止跳过 API 合同直接实现
- 禁止使用 emoji
- **禁止删除 `data/` 目录及其内容**（用户数据库 + 上传图片）
- **禁止删除 `dist/data/` 目录及其内容**（exe 模式用户数据，与开发模式 `data/` 隔离）
- **禁止 `rm -rf dist`**（会连带删除 `dist/data/` 用户数据），重建 exe 只删 `build/` 和 `dist/*.exe`
- **禁止将 `dist/Self-Grow.exe` 复制到项目根目录**（打包产物唯一位置是 `./dist/`）
- 禁止删除 `data/images/role_models/` 中的种子图片

## 构建与打包命令
- 前端构建: `cd frontend && npm run build`
- 重建 exe: `rm -rf build && rm -f dist/Self-Grow.exe && venv/Scripts/python -m PyInstaller Self-Grow.spec --noconfirm`
- **注意**: 重建 exe 时只删 `build/` 和 `dist/Self-Grow.exe`，不删 `dist/data/`
