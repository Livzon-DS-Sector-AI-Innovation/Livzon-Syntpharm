# 设备批量导入 v2 - 技术规格书

## 1. API 接口定义

### 1.1 下载模板
*   **URL**: `GET /api/v1/equipment/equipments/import/template`
*   **响应**: Base64 编码的 `.xlsx` 文件。

### 1.2 数据预览
*   **URL**: `POST /api/v1/equipment/equipments/import/preview`
*   **Payload**: JSON 数组（由前端解析 Excel 后发送）。
*   **逻辑**: 执行 `DEPT_MAPPING_V2` 映射并查询 `hr.departments` 验证存在性。

### 1.3 批量导入
*   **URL**: `POST /api/v1/equipment/equipments/import/batch`
*   **逻辑**: 逐行处理，成功则入库，失败则记录错误，最后返回汇总报告。

## 2. 部门映射规范 (DEPT_MAPPING_V2)

| Excel 原始名称 | 数据库标准名称 (hr.departments) |
| :--- | :--- |
| 检验室 | 质量控制部 |
| 头孢合成一车间 | 201车间 |
| 非头孢一车间 | 101车间 |
| 溶剂回收车间-404岗 | 溶剂回收车间 |
| ... | ... (共 38 项) |

## 3. 异常处理
*   **部门不存在**: 标记为 `validation_error`，不中断整体流程。
*   **资产编号重复**: 自动跳过并计入 `skipped_count`。
*   **必填项缺失**: 返回具体字段错误提示。
