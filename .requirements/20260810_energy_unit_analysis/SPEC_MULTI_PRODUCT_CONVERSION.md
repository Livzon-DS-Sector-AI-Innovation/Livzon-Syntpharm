# 技术规格说明书：能源单耗分析 V2 (多产品与标准品折算)

## 1. 摘要
升级 AI 能耗分析功能，支持多产品产量录入及标准品折算逻辑。通过引入“产品折算系数”配置表和预留生产数据接口，解决因产品结构变化导致的单耗波动误判问题。

## 2. 核心逻辑定义
*   **折算总产量** = $\sum (\text{产品}_i \text{产量} \times \text{产品}_i \text{折算系数})$
*   **实际单耗** = $\frac{\text{车间当月总能耗}}{\text{折算总产量}}$
*   **基准产品**：选定一种主要产品，其折算系数定义为 `1.0`。

## 3. 接口契约 (API Contracts)

### 3.1 新增：获取生产产出数据
*   **Path**: `GET /api/v1/production/output`
*   **Params**: `workshop_id` (UUID), `month` (YYYY-MM)
*   **Response**:
    ```json
    {
      "code": 200,
      "data": {
        "workshop_id": "uuid",
        "month": "2026-08",
        "items": [
          { "product_name": "阿莫西林", "quantity": 1000, "unit": "kg" },
          { "product_name": "辅料包材", "quantity": 5000, "unit": "kg" }
        ]
      }
    }
    ```

### 3.2 修改：AI 能耗智能分析 V2
*   **Path**: `POST /api/v1/energy/ai-analysis-v2`
*   **Request Body 变更**:
    ```typescript
    interface ProductionItem {
      product_name: string;
      quantity: number;
      unit?: string;
    }
    
    interface AIAnalysisRequest {
      workshop_id: string;
      analysis_month: string;
      production_items: ProductionItem[]; // 替代原有的 manual_production
      include_ai_suggestion?: boolean;
    }
    ```

## 4. 数据库变更 (Migration)
*   **文件**: `backend/alembic/versions/0054_add_product_conversion.py`
*   **表名**: `energy_product_conversions`
*   **字段**:
    *   `id`: UUID (PK)
    *   `product_name`: String(128) (Unique)
    *   `conversion_factor`: Numeric(10, 4) (Default 1.0)
    *   `description`: Text (Nullable)

## 5. 前端交互规范
*   **动态录入**：在 AI 分析页面，产量输入区改为表格形式，支持“添加行”。
*   **系数匹配**：前端根据用户输入的产品名称，自动从后端配置表匹配 `conversion_factor` 并显示。
*   **兜底方案**：若生产接口无数据，提供“手动估算总产量”开关，此时不进行折算。

## 6. 验收标准 (Acceptance Criteria)
1.  [ ] 数据库中存在 `energy_product_conversions` 表且已初始化至少 2 条测试数据。
2.  [ ] 调用 `ai-analysis-v2` 接口时，传入多产品列表，后端能正确计算出折算后的单耗。
3.  [ ] AI 返回的分析报告中，能准确引用各产品的产量占比信息。
4.  [ ] 前端页面能正常展示多行产品录入框，并能成功触发分析请求。

## 7. 假设与默认值
*   **基准产品**：默认选择能耗最高的主要产品作为系数 1.0 的基准。
*   **数据缺失**：若某产品在配置表中找不到系数，默认按 1.0 处理并记录警告日志。
*   **生产接口**：在生产模块开发完成前，前端默认展示手动录入界面。
