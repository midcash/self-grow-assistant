# API 接口协议 v1.2

> 成熟度: 🟢 稳定 — 39 个端点已在前后端联调中验证。

本文件是后端和前端之间的 Sprint Contract。Team Lead 维护，双方 Agent 只读遵守。
接口变更必须先从本文档开始。

---

## 通用约定

- Base URL: `/api/v1`
- Content-Type: `application/json`
- 认证：v1 暂不实现，后续扩展

### 统一响应格式

成功：
```json
{ "code": 0, "message": "success", "data": {} }
```

失败：
```json
{ "code": 40001, "message": "品质目标不存在", "data": null }
```

### 分页参数
- 请求：`?page=1&page_size=20`
- 响应 data 中附带 `{ "items": [], "total": 100, "page": 1, "page_size": 20 }`

---

## 1. 品质目标 APIs

### 1.1 创建品质目标
```
POST /api/v1/qualities
Body: { "name": "自律", "description": "坚持完成每日计划", "icon": "star", "target_level": 3 }
Response: { "code": 0, "data": { Quality对象 } }
```

### 1.2 获取品质列表
```
GET /api/v1/qualities?is_active=true
Response: { "code": 0, "data": { "items": [...Quality], "total": N } }
```

### 1.3 获取单个品质详情
```
GET /api/v1/qualities/{id}
Response: {
  "code": 0,
  "data": {
    "id": 1, "name": "自律", "description": "...", "icon": "star",
    "target_level": 3, "current_level": 1, "total_score": 85,
    "levels": [{ "level": 1, "name": "萌芽期", "threshold_score": 0 }, ...],
    "progress": [{ "date": "2026-04-28", "score": 10 }, ...]
  }
}
```

### 1.4 更新品质目标
```
PUT /api/v1/qualities/{id}
Body: { "name": "...", "description": "...", "icon": "...", "target_level": 4 }
Response: { "code": 0, "data": { Quality对象 } }
```

### 1.5 删除（软删除）品质目标
```
DELETE /api/v1/qualities/{id}
Response: { "code": 0, "message": "已停用" }
```

### 1.6 更新分类映射
```
PUT /api/v1/qualities/{id}/mappings
Body: {
  "mappings": [
    { "category": "学习", "score_per_duration": 0.05, "score_per_completion": 5 },
    { "category": "运动", "score_per_duration": 0.1,  "score_per_completion": 10 }
  ]
}
Response: { "code": 0, "data": { "mappings": [...] } }
```

---

## 2. TODO APIs

### 2.1 智能解析日程文本
```
POST /api/v1/todos/parse
Body: { "text": "上午读2h《原则》，下午跑步40分钟", "date": "2026-04-30" }
Response: {
  "code": 0,
  "data": {
    "parsed": [
      { "content": "读《原则》", "category": "学习", "duration_minutes": 120 },
      { "content": "跑步", "category": "运动", "duration_minutes": 40 }
    ]
  }
}
```
注：v1 使用规则解析（正则+关键词），以合理结构和准确性作为设计原则

### 2.2 批量保存 TODO
```
POST /api/v1/todos/batch
Body: {
  "date": "2026-04-30",
  "todos": [
    { "content": "...", "category": "学习", "duration_minutes": 120 },
    { "content": "...", "category": "运动", "duration_minutes": 40 }
  ]
}
Response: { "code": 0, "data": { "items": [...TodoItem] } }
```

### 2.3 获取指定日期 TODO 列表
```
GET /api/v1/todos?date=2026-04-30
Response: { "code": 0, "data": { "items": [...TodoItem] } }
```

### 2.4 打卡完成单条 TODO
```
PATCH /api/v1/todos/{id}/checkin
Body: { "actual_duration": 110 }
Response: {
  "code": 0,
  "data": {
    "todo": { TodoItem对象, status="done" },
    "score_earned": 11    ← 该完成获得的积分
  }
}
```

### 2.5 跳过单条 TODO
```
PATCH /api/v1/todos/{id}/skip
Response: { "code": 0, "data": { TodoItem对象, status="skipped" } }
```

### 2.6 更新单条 TODO
```
PUT /api/v1/todos/{id}
Body: { "content": "...", "category": "...", "duration_minutes": ... }
Response: { "code": 0, "data": { TodoItem对象 } }
```

### 2.7 删除单条 TODO
```
DELETE /api/v1/todos/{id}
Response: { "code": 0, "message": "已删除" }
```

---

## 3. 进度与统计 APIs

### 3.1 获取今日总览
```
GET /api/v1/progress/dashboard?date=2026-04-30
Response: {
  "code": 0,
  "data": {
    "date": "2026-04-30",
    "completion_rate": 0.75,           ← 今日完成率
    "total_duration": 280,             ← 今日总投入分钟数
    "total_score_today": 42,           ← 今日获得总积分
    "streak_days": 7,                  ← 连续打卡天数
    "qualities": [
      {
        "id": 1, "name": "自律", "icon": "star",
        "current_score": 85, "current_level": 1,
        "level_name": "萌芽期",
        "next_level_name": "习惯期",
        "next_level_score": 100,
        "progress_pct": 85.0
      }
    ],
    "todos": [...TodoItem]             ← 今日 TODO 列表
  }
}
```

### 3.2 获取单个品质的积分历史
```
GET /api/v1/progress/qualities/{id}/history?days=30
Response: {
  "code": 0,
  "data": {
    "quality": { Quality对象 },
    "history": [
      { "date": "2026-04-01", "score": 10, "total_score": 10 }
    ]
  }
}
```

### 3.3 获取热力图数据
```
GET /api/v1/progress/heatmap?start_date=2026-04-01&end_date=2026-04-30
Response: {
  "code": 0,
  "data": {
    "categories": ["学习", "运动", "工作", "生活", "阅读", "冥想"],
    "data": [
      { "date": "2026-04-01", "学习": 120, "运动": 40, "工作": 0, ... },
      ...
    ]
  }
}
```

### 3.4 获取趋势数据（折线图）
```
GET /api/v1/progress/trend?quality_id=1&days=30
Response: {
  "code": 0,
  "data": {
    "quality_name": "自律",
    "points": [
      { "date": "2026-04-01", "cumulative_score": 10 },
      { "date": "2026-04-02", "cumulative_score": 25 },
      ...
    ],
    "level_thresholds": [0, 100, 300, 600, 1000, 1000]   ← 各等级分数线
  }
}
```

---

## 4. 报告 APIs

### 4.1 获取文字总结
```
GET /api/v1/reports/summary?type=weekly&date=2026-04-30
Response: {
  "code": 0,
  "data": {
    "period": "2026-04-24 ~ 2026-04-30",
    "total_duration": 1680,
    "total_score": 312,
    "streak_days": 7,
    "top_quality": { "name": "自律", "score_gained": 85 },
    "insight": "你已连续7天完成计划，自律值从32%提升到42%。阅读时长比上周增加40%。再坚持5天即可达到等级2'习惯期'。"
  }
}
```

---

## 5. 明星榜样 APIs

### 5.1 获取明星榜样列表
```
GET /api/v1/role-models
Response: {
  "code": 0,
  "data": [
    {
      "id": 1, "name": "沈腾", "field": "演员 / 喜剧人", "avatar": "theater",
      "image_url": "/api/v1/static/images/role_models/shenteng.png",
      "description": "...",
      "qualities": [
        {
          "id": 1, "role_model_id": 1, "quality_name": "高情商",
          "description": "...",
          "suggested_activities": [
            { "content": "情绪日记：...", "category": "生活", "duration_minutes": 10, "frequency": "每日", "reason": "..." }
          ]
        }
      ]
    }
  ]
}
```

### 5.2 获取单个明星详情
```
GET /api/v1/role-models/{id}
Response: { "code": 0, "data": { 同列表中的单个对象 } }
```

### 5.3 采纳明星品质为目标
```
POST /api/v1/role-models/{role_model_id}/adopt/{quality_id}
Response: {
  "code": 0,
  "data": {
    "quality_id": 1,
    "quality_name": "高情商",
    "role_model_name": "沈腾",
    "message": "已创建品质'高情商'，系统将根据日常打卡自动计算积分。"
  }
}
```
注：重复采纳同名品质会返回已有 quality_id，不会重复创建。

### 5.4 上传明星图片
```
POST /api/v1/role-models/{role_model_id}/upload-image
Content-Type: multipart/form-data
Body: file=<图片文件>  (支持 jpg/png/webp/gif)
Response: {
  "code": 0,
  "data": {
    "image_url": "/api/v1/static/images/role_models/abc123.jpg"
  }
}
```
注：上传后自动更新对应 RoleModel 的 image_url 字段。

---

## 6. 看板背景图 APIs

### 6.1 获取当前背景图
```
GET /api/v1/dashboard/background
Response: {
  "code": 0,
  "data": {
    "image_url": "/api/v1/static/images/dashboard/background.png"  // 无背景时为 null
  }
}
```

### 6.2 上传背景图
```
POST /api/v1/dashboard/background
Content-Type: multipart/form-data
Body: file=<图片文件>  (支持 jpg/png/webp/gif)
Response: {
  "code": 0,
  "data": {
    "image_url": "/api/v1/static/images/dashboard/background.png"
  }
}
```
注：上传新图会自动替换旧图，仅保留一张背景图。

---

## 错误码定义

| code | 说明 |
|------|------|
| 0 | 成功 |
| 40001 | 品质目标不存在 |
| 40002 | TODO 不存在 |
| 40003 | 必填字段缺失 |
| 40004 | 参数格式错误 |
| 40005 | 日期格式错误 |
| 50000 | 服务器内部错误 |

---

## 注意事项
1. 所有日期字段格式为 `YYYY-MM-DD`
2. 所有时间字段格式为 ISO 8601 `YYYY-MM-DDTHH:MM:SS`
3. 积分计算在后端执行（基于 CategoryMapping），前端不重复计算
4. 打卡完成时后端同步更新 QualityProgress 表
5. 每日首次打开 Dashboard 时触发当天 QualityProgress 快照初始化（若无记录则创建当日 0 分记录）
