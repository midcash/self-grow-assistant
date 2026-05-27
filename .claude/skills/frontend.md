# Frontend Agent Skill

你是本项目的前端开发 Agent。你的职责是实现 `frontend/` 下所有代码。

## 技术约束
- Vue 3（Composition API + `<script setup>`）+ Vite + TypeScript
- UI 框架：Tailwind CSS
- 图表库：ECharts（通过 `vue-echarts` 封装）
- 路由：Vue Router 4
- HTTP：axios 或 fetch，统一错误拦截
- 构建产物输出到项目根目录 `static/`，供后端 serve
- 所有 API 调用以 `/api/v1/` 开头，开发时通过 Vite proxy 转发到后端

## 目录职责
```
frontend/
├── index.html
├── vite.config.ts
├── package.json
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/
│   │   └── index.ts
│   ├── api/
│   │   ├── request.ts       ← axios 实例，统一错误处理
│   │   ├── qualities.ts     ← 品质相关 API
│   │   ├── todos.ts         ← TODO 相关 API
│   │   └── progress.ts      ← 进度相关 API
│   ├── views/
│   │   ├── Dashboard.vue    ← 首页看板（品质总览 + 今日 TODO）
│   │   ├── Qualities.vue    ← 品质目标管理页
│   │   ├── DailyInput.vue   ← 日程录入页
│   │   ├── CheckIn.vue      ← 打卡页
│   │   └── Report.vue       ← 成长报告页（图表集中）
│   ├── components/
│   │   ├── NavBar.vue       ← 底部导航栏
│   │   ├── QualityCard.vue  ← 品质卡片（头像+进度条）
│   │   ├── TodoItem.vue     ← 单条 TODO
│   │   ├── RadarChart.vue   ← 品质雷达图
│   │   ├── Heatmap.vue      ← 学习热力图（类似 GitHub 贡献图）
│   │   └── TrendLine.vue    ← 成长趋势折线图
│   └── types/
│       └── index.ts         ← 前端类型定义（手动对齐后端模型）
```

## 页面功能细节

### Dashboard（首页看板）
- 顶部：日期选择器（默认今天）
- 中部：ECharts 雷达图（展示各品质成长百分比，如自律 35%、执行力 60%）
- 下部：今日 TODO 列表（展示完成状态，支持快速勾选打卡）
- 统计栏：今日完成率、本周连续打卡天数、总学习时长

### Qualities（品质管理）
- 可拖拽排序的品质卡片列表
- 每张卡片：名称、描述、图标、目标等级、当前等级、当前积分
- 点击进入详情：该品质的等级阶梯说明 + 关联的 TODO 分类 + 积分历史
- 浮动按钮：新增品质 + 编辑映射规则

### DailyInput（日程录入）
- 顶部日期选择器
- 文本输入框（多行），输入一天安排
- "智能解析"按钮：调用后端 `/api/v1/todos/parse` 解析文本为 TODO 列表
- 下方展示解析后的 TODO 列表，可手动增删改
- 确认后批量保存

### CheckIn（打卡页）
- 展示今日所有 TODO，按分类分组
- 每条：点击复选框标记完成 + 可选填写实际时长
- 完成时轻微动效反馈（绿色勾 + 进度条跳动）
- 顶部显示"今日已获得 X 积分"

### Report（成长报告）
- 时间范围选择：近 7 天 / 30 天 / 自定义
- 热力图：横轴日期 × 纵轴分类，颜色深浅 = 时长
- 趋势折线图：选中单个品质，展示积分增长曲线，标注等级跃迁点
- 文字总结："你已经连续 XX 天完成计划，自律值达到 XX%，距离下一等级'习惯期'还需 XX 分"

## 设计规范
- 整体风格：简洁、现代、明亮，避免"AI 风"（紫色渐变背景 + 白色卡片 = 禁止）
- 主色调：暖橙色或柔和绿色（代表成长）
- 字体：系统原生字体栈，不引入 Google Font
- 动效：仅用于状态切换（完成打卡、等级提升），不滥用
- 移动端优先：底部导航栏，卡片式布局
- 暗色模式暂不做

## Vite 配置
- 开发代理：`/api` → `http://localhost:8000`
- 构建输出：`../static/`
- 路径 base：`./`（相对路径，适配 exe 内嵌）

## 必须遵守的规则
1. 所有 API 调用前先读 `contracts/api-spec.md` 确认接口签名
2. 不得修改 `backend/` 目录下的任何文件
3. 写完页面后用 `npm run build` 验证构建通过
4. 前端类型定义（`types/index.ts`）必须手动对齐后端 Pydantic schemas
5. 不要使用 emoji
