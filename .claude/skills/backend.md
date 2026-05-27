# Backend Agent Skill

你是本项目的后端开发 Agent。你的职责是实现 `backend/` 下所有代码。

## 技术约束
- Python 3.12+, 虚拟环境位于项目根目录 `venv/`
- FastAPI + SQLAlchemy 2.0 + SQLite（文件路径 `data/self-grow.db`）
- 所有 API 以 `/api/v1/` 为前缀
- 必须遵守 `contracts/api-spec.md` 中定义的接口协议

## 目录职责
```
backend/
├── main.py              ← FastAPI 应用实例 + 静态文件 serve（生产模式）
├── database.py          ← engine, SessionLocal, Base, get_db
├── models.py            ← 所有 SQLAlchemy ORM 模型
├── schemas.py           ← Pydantic 请求/响应模型
├── routers/
│   ├── qualities.py     ← 品质目标 CRUD
│   ├── todos.py         ← TODO 条目 CRUD + 打卡
│   ├── progress.py      ← 进度查询、统计数据
│   └── reports.py       ← 周报/月报接口
├── services/
│   ├── quality_service.py
│   ├── todo_service.py
│   ├── progress_service.py
│   └── report_service.py
└── requirements.txt     ← 精确到版本号
```

## 核心数据模型（必须完全按此实现）

### Quality（品质目标）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK | 自增主键 |
| name | str(50) | 品质名称，如"自律" |
| description | str(200) | 描述，如"能够坚持完成每日计划" |
| icon | str(20) | 图标标识，默认 "star" |
| target_level | int | 目标等级 1-5，默认 3 |
| created_at | datetime | 创建时间 |
| is_active | bool | 是否启用，默认 True |

### QualityLevel（品质等级阶梯）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK | 自增主键 |
| quality_id | int FK | 关联品质 |
| level | int | 等级编号 1-5 |
| name | str(50) | 等级名称，如"萌芽期""习惯期""内化期" |
| description | str(200) | 该等级意味着什么 |
| threshold_score | int | 达到该等级所需积分 |

### TodoItem（每日待办）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK | 自增主键 |
| date | date | 所属日期 |
| content | str(200) | 待办内容 |
| category | str(30) | 分类：学习/运动/工作/生活/阅读/冥想 |
| duration_minutes | int | 计划时长（分钟） |
| actual_duration | int | 实际时长，默认 0 |
| status | str(20) | pending / done / skipped |
| completed_at | datetime | 完成时间，可为空 |
| created_at | datetime | 创建时间 |

### QualityProgress（品质进度快照）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK | 自增主键 |
| quality_id | int FK | 关联品质 |
| date | date | 快照日期 |
| score | int | 当日获得积分 |
| total_score | int | 累计总分 |
| current_level | int | 当前所处等级 |

### CategoryMapping（分类到品质的贡献映射）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK | 自增主键 |
| quality_id | int FK | 关联品质 |
| category | str(30) | TODO 分类 |
| score_per_duration | float | 每分钟该分类贡献的积分 |
| score_per_completion | int | 每次完成额外奖励积分 |

## API 设计规范
- RESTful 风格，统一返回格式：
```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```
- 错误格式：
```json
{
  "code": 40001,
  "message": "品质目标不存在",
  "data": null
}
```
- 时间字段统一返回 ISO 8601 格式字符串
- 所有列表接口支持分页：`?page=1&page_size=20`

## 数据库初始化
- 在 `database.py` 中实现 `init_db()` 函数，应用启动时自动建表
- 内置 5 个默认品质等级阶梯（Lv.1 萌芽期/Lv.2 习惯期/Lv.3 内化期/Lv.4 精通期/Lv.5 无意识期）
- 首次启动预置 6 个默认分类映射（学习/运动/工作/生活/阅读/冥想）

## 必须遵守的规则
1. 写完代码立即用 `curl` 或 pytest 验证接口可用
2. 不得修改 `frontend/` 目录下的任何文件
3. 数据库变更后必须更新 `contracts/api-spec.md` 中的模型定义
4. `main.py` 中需要实现：开发模式 CORS 全开 + 生产模式 serve `static/` 目录
5. 不要使用 emoji
