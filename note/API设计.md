# API 设计方案 - Phase 1 新增模块

**更新日期**: 2026-08-28

---

## 一、立项与开题模块

### 创建立项开题

```http
POST /api/research/initiations
Content-Type: application/json
Authorization: Bearer <token>

{
  "project_id": "uuid",
  "market_research": "市场分析内容...",
  "patent_analysis": "专利分析内容...",
  "sales_data": {...},
  "development_strategy": "申报策略...",
  "target_product_profile": {...},
  "synthetic_route": "合成路线描述...",
  "starting_materials": [...],
  "cqas": [...],
  "cpps": [...],
  "gantt_chart": {...},
  "material_budget": {...},
  "labor_budget": {...},
  "total_cost_estimate": 100000.00
}
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "project_id": "uuid",
    "status": "draft",
    "created_at": "2026-08-28T10:00:00Z"
  },
  "message": "创建成功"
}
```

### 获取立项开题详情

```http
GET /api/research/initiations/{id}
Authorization: Bearer <token>
```

### 更新立项开题

```http
PUT /api/research/initiations/{id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "market_research": "更新后的内容...",
  ...
}
```

### 审批立项开题

```http
POST /api/research/initiations/{id}/approve
Authorization: Bearer <token>
```

---

## 二、小试验证模块

### 创建小试批次

```http
POST /api/research/lab-validation-batches
Content-Type: application/json
Authorization: Bearer <token>

{
  "project_id": "uuid",
  "batch_no": "LAB-2026-001",
  "batch_sequence": 1,
  "process_parameters": {...},
  "start_date": "2026-09-01"
}
```

### 获取项目的小试验证列表

```http
GET /api/research/projects/{project_id}/lab-validation
Authorization: Bearer <token>
```

**响应**:
```json
{
  "code": 200,
  "data": {
    "batches": [
      {
        "id": "uuid",
        "batch_no": "LAB-2026-001",
        "batch_sequence": 1,
        "status": "completed",
        "yield_pct": 85.5,
        "purity_pct": 99.6
      }
    ],
    "pre_stability_studies": [...]
  }
}
```

### 更新小试批次

```http
PUT /api/research/lab-validation-batches/{id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "yield_pct": 85.5,
  "purity_pct": 99.6,
  "qc_results": {...},
  "impurity_profile": {...},
  "status": "completed",
  "end_date": "2026-09-05"
}
```

### 创建预稳定性实验

```http
POST /api/research/pre-stability
Content-Type: application/json
Authorization: Bearer <token>

{
  "project_id": "uuid",
  "batch_id": "uuid",
  "study_type": "accelerated",
  "conditions": {"temperature": 40, "humidity": 75},
  "time_points": [0, 7, 14, 30, 60, 90]
}
```

---

## 三、中试研究模块

### 创建中试批次

```http
POST /api/research/pilot-batches
Content-Type: application/json
Authorization: Bearer <token>

{
  "project_id": "uuid",
  "batch_no": "PILOT-2026-001",
  "scale_kg": 10.0,
  "equipment_used": ["反应釜A", "离心机B"],
  "operators": ["user_uuid_1", "user_uuid_2"],
  "start_date": "2026-10-01"
}
```

### 获取项目的中试批次列表

```http
GET /api/research/projects/{project_id}/pilot-batches
Authorization: Bearer <token>
```

### 创建清洁方案

```http
POST /api/research/cleaning-protocols
Content-Type: application/json
Authorization: Bearer <token>

{
  "project_id": "uuid",
  "equipment_id": "reactor_A",
  "cleaning_method": "CIP清洗流程...",
  "acceptance_criteria": {
    "limit_ppm": 10,
    "pde_value": 0.5
  }
}
```

### 创建工艺规程

```http
POST /api/research/process-specifications
Content-Type: application/json
Authorization: Bearer <token>

{
  "project_id": "uuid",
  "version": 1,
  "content_md": "# 工艺规程\n\n## 步骤1...\n",
  "critical_steps": [...],
  "parameters_range": {...}
}
```

### 创建批生产记录

```http
POST /api/research/batch-records
Content-Type: application/json
Authorization: Bearer <token>

{
  "pilot_batch_id": "uuid",
  "template_id": "uuid",
  "filled_data": {...}
}
```

### 签署批记录

```http
POST /api/research/batch-records/{id}/sign
Content-Type: application/json
Authorization: Bearer <token>
```

---

## 四、杂质研究增强

### 创建杂质合成跟踪

```http
POST /api/research/impurity-synthesis
Content-Type: application/json
Authorization: Bearer <token>

{
  "impurity_id": "uuid",
  "synthesis_route": "合成路线描述...",
  "intermediates": ["中间体A", "中间体B"]
}
```

### 更新杂质合成进度

```http
PUT /api/research/impurity-synthesis/{id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "final_yield": 65.5,
  "purity": 98.2,
  "structure_confirmed": true,
  "nmr_data_file": "uuid",
  "ms_data_file": "uuid",
  "status": "confirmed"
}
```

---

## 五、任务协作模块

### 创建任务

```http
POST /api/research/tasks
Content-Type: application/json
Authorization: Bearer <token>

{
  "project_id": "uuid",
  "title": "完成小试第一批",
  "description": "详细描述...",
  "assignee_id": "user_uuid",
  "due_date": "2026-09-15",
  "priority": "high"
}
```

### 获取项目任务列表

```http
GET /api/research/projects/{project_id}/tasks
Authorization: Bearer <token>
```

### 获取我的任务

```http
GET /api/research/tasks/my
Authorization: Bearer <token>
```

### 更新任务状态

```http
PUT /api/research/tasks/{id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "status": "in_progress"
}
```

---

## 六、错误响应格式

所有API错误统一返回格式：

```json
{
  "code": 400,
  "error": {
    "type": "validation_error",
    "message": "参数验证失败",
    "details": [
      {
        "field": "batch_sequence",
        "message": "必须是 1、2 或 3"
      }
    ]
  }
}
```

常见错误码：
- `400`: 请求参数错误
- `401`: 未授权
- `403`: 权限不足
- `404`: 资源不存在
- `409`: 冲突（如重复创建）
- `500`: 服务器内部错误

---

## 七、权限控制

| 角色 | 立项开题 | 小试验证 | 中试研究 | 杂质合成 | 任务管理 |
|------|---------|---------|---------|---------|---------|
| 研究员 | 读写 | 读写 | 读写 | 读写 | 读写 |
| QA | 只读 | 只读 | 只读 | 只读 | 只读 |
| 项目经理 | 读写+审批 | 读写 | 读写 | 读写 | 读写+分配 |
| 管理员 | 全部 | 全部 | 全部 | 全部 | 全部 |

---

## 八、审计追踪

所有写操作自动记录审计日志：

```python
# 自动记录的字段
{
  "entity_type": "LabValidationBatch",
  "entity_id": "uuid",
  "action": "update",
  "old_value": {...},
  "new_value": {...},
  "user_id": "uuid",
  "timestamp": "2026-08-28T10:00:00Z",
  "reason": "更新收率和纯度数据",
  "ip_address": "192.168.1.100"
}
```
