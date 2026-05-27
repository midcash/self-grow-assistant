# 开发进度 — self-grow 自我成长可视化系统

> 最后更新: 2026-05-03
> 更新者: Claude Code
> 构建状态: 通过 (v1.4.1 任务详情弹窗 + 窗口适配)

---

## 模块清单

### Backend (100% 代码完成, 已验证)
| 模块 | 文件 | 状态 | 验证 | 备注 |
|------|------|------|------|------|
| 数据库连接 | database.py | 完成 | 联调通过 | SQLite WAL + 外键，路径 data/self-grow.db |
| ORM 模型 | models.py | 完成 | 联调通过 | 7 表: +RoleModel/RoleModelQuality (v1.2) |
| Pydantic Schema | schemas.py | 完成 | 联调通过 | 全部请求/响应模型，含分页包装(未使用) |
| FastAPI 入口 | main.py | 完成 | 联调通过 | CORS + lifespan + /api/health + 生产静态文件serve |
| 品质目标路由 | routers/qualities.py | 完成 | 联调通过 | 6 端点: CRUD + mappings 更新 |
| TODO 路由 | routers/todos.py | 完成 | 联调通过 | 7 端点: parse/batch/CRUD/checkin/skip |
| 进度统计路由 | routers/progress.py | 完成 | 联调通过 | 4 端点: dashboard/history/heatmap/trend |
| 报告路由 | routers/reports.py | 完成 | 联调通过 | 1 端点: summary (weekly/monthly) |
| 品质服务 | services/quality_service.py | 完成 | 联调通过 | 含默认5级阶梯 + 6类映射初始化 |
| TODO 服务 | services/todo_service.py | 完成 | 联调通过 | 规则解析 + 批量保存 + 打卡积分计算 |
| 进度服务 | services/progress_service.py | 完成 | 联调通过 | Dashboard聚合 + 历史 + 热力图 + 趋势 |
| 报告服务 | services/report_service.py | 完成 | 联调通过 | 周/月报 + streak计算 + AI文字洞察 |
| 启动器 | run.py | 完成 | 联调通过 | pywebview 原生窗口 + 后台 FastAPI |
| 明星榜样服务 | services/role_model_service.py | 完成 | 联调通过 | 12位明星 + 16项品质 + 48条推荐活动 + 种子数据初始化 |
| 明星榜样路由 | routers/role_models.py | 完成 | 联调通过 | 4 端点: 列表/详情/采纳/上传图片 |
| Dashboard 背景路由 | routers/dashboard_bg.py | 完成 | 联调通过 | 2 端点: 获取/上传背景图 |

API 端点总计: 24/24 实现 (对齐 contracts/api-spec.md v1.2)

### Frontend (100% 代码完成, build 通过)
| 页面/组件 | 文件 | 状态 | 验证 | 备注 |
|-----------|------|------|------|------|
| 路由配置 | router/index.ts | 完成 | build通过 | 6 路由, hash模式, 懒加载 |
| 类型定义 | types/index.ts | 完成 | — | 手动对齐后端 Pydantic schema |
| HTTP 封装 | api/request.ts | 完成 | build通过 | axios + 统一错误拦截 |
| Dashboard 页 | views/Dashboard.vue | 完成 | build通过 | 日期选择 + 背景图横幅 + 雷达图 + 品质卡片 + TODO列表 |
| 品质管理页 | views/Qualities.vue | 完成 | build通过 | 品质卡片列表 |
| 日程录入页 | views/DailyInput.vue | 完成 | build通过 | 文本输入 + 智能解析 + 批量保存 |
| 打卡页 | views/CheckIn.vue | 完成 | build通过 | 按分类分组 + 完成/跳过 |
| 报告页 | views/Report.vue | 完成 | build通过 | 热力图 + 趋势折线图 + 文字总结 |
| 导航栏 | components/NavBar.vue | 完成 | build通过 | 底部 6 Tab |
| 品质卡片 | components/QualityCard.vue | 完成 | build通过 | 头像 + 进度条 |
| TODO 条目 | components/TodoItem.vue | 完成 | build通过 | 单条展示 + 操作按钮 |
| 雷达图 | components/RadarChart.vue | 完成 | build通过 | ECharts 雷达图 |
| 热力图 | components/Heatmap.vue | 完成 | build通过 | 类似 GitHub 贡献图 |
| 趋势线 | components/TrendLine.vue | 完成 | build通过 | ECharts 折线图 |
| 明星榜样页 | views/RoleModels.vue | 完成 | build通过 | 明星卡片列表 + 品质详情 + 推荐活动 + 采纳按钮 |

## 当前版本

- **版本**: v1.4.1
- **API 协议**: contracts/api-spec.md v1.2
- **前端构建**: `npm run build` 通过，输出到 static/
- **打包**: `./dist/Self-Grow.exe` (22MB) 已生成，PyInstaller + pywebview 打包成功，含种子图片
- **运行方式**: 双击 `dist/Self-Grow.exe` 或 `venv/Scripts/python run.py` → 后台启动 FastAPI → 原生窗口加载
- **数据库**: data/self-grow.db 已初始化，WAL 模式，含 image_url 迁移
- **认证**: 未实现 (api-spec 声明 "v1 暂不实现")

## 已知问题

| # | 问题描述 | 严重程度 | 状态 |
|---|---------|---------|------|
| 1 | backend/skills 描述 QualityProgress 有 current_level 字段，但 models.py 中缺失 | 中 | 待确认 |
| 2 | schemas.py 定义了 PaginatedData 但所有列表接口未使用分页 | 低 | 待优化 |
| 3 | report_service.py streak 仅判断"有任一 todo 完成"即算连续，边界宽松 | 低 | 待确认 |

## 本次变更摘要

- **任务详情弹窗 + 窗口适配 (v1.4.1)**：两个体验优化
  - TodoItem.vue 新增"详情"按钮，点击弹出遮罩弹窗展示完整任务内容（含分类、状态、时长、时间戳）
  - style.css `#app` 移除 `max-width: 480px` + `margin: 0 auto`，改为 `width: 100%` 撑满窗口
  - run.py 窗口宽度 1200 → 500，min_size (800,600) → (400,500)
  - Self-Grow.exe 已重新打包

### 历史变更 (v1.4.0)
  - 新增 `backend/routers/dashboard_bg.py`：2 端点 (GET/POST /dashboard/background)，基于文件系统，无需数据库变更
  - 上传自动替换旧图，仅保留一张背景图
  - 智能横竖图适配：Pillow + EXIF 方向检测，`ImageOps.exif_transpose` 处理手机竖拍照片
  - 横图 `h-40` (160px)，竖图 `h-96` (384px)，自动切换
  - 前端 Dashboard.vue：统计行下方横幅，无背景时渐变占位 + 引导文案，hover "更换背景"
  - contracts/api-spec.md 新增第 6 章
  - API 端点总数: 22 → 24
  - CLAUDE.md 新增数据保护规则：`data/`、`dist/data/` 禁止删除，`rm -rf dist` 禁止，重建 exe 安全命令
  - CLAUDE.md 新增「构建与打包命令」章节

### 历史变更 (v1.3.0)
- **明星图片功能**：RoleModel 新增 image_url 字段，支持上传自定义图片和默认占位图
  - 数据库迁移：ALTER TABLE 添加 image_url 列，已有数据自动回填默认图片路径
  - API 新增 1 个端点：POST /role-models/{id}/upload-image (multipart/form-data)，总计 22 端点
  - API 新增静态文件挂载：/api/v1/static/images → data/images/
  - 前端：头像区域 hover 显示上传按钮，上传中显示加载态，加载失败自动降级为 SVG 图标
  - 预置 12 张彩色占位图 (data/images/role_models/)，Pillow 生成，显示明星姓名
  - 新增依赖：python-multipart, Pillow
  - contracts/api-spec.md 更新至 v1.2
  - Self-Grow.exe 重新打包：datas 新增 data/images，hiddenimports 新增 python_multipart/PIL
  - 新增 _ensure_seed_images()：frozen 模式下自动从 _MEIPASS 复制种子图片到 data/ 目录
  - 新增 api/request.ts upload() 方法：FormData multipart 上传
  - CLAUDE.md 补充开发启动路径文档（run.py / uvicorn / npm run dev）

### 历史变更 (v1.2.0)
- 明星榜样功能：RoleModel + RoleModelQuality 数据模型，12 位明星、16 项品质、48 条推荐活动
- API 新增 3 端点：GET/POST role-models，采纳品质自动创建 Quality + levels + mappings
- 前端新增"榜样"Tab
- 修复: RoleModels.vue 漏引 NavBar

## 下次开发计划

- [ ] 中: 核查 QualityProgress.current_level 字段是否需要在 models.py 中补充
- [ ] 低: 列表接口加入分页支持
- [ ] 低: 认证模块 (OAuth2/JWT) 设计
