# AI Parser 模块

实验记录和工艺参数的智能解析模块，基于LLM实现结构化数据提取。

## 功能概述

- **实验记录解析**: 从小试确认或放大生产的实验记录文本中提取结构化数据
- **工艺参数解析**: 从工艺描述文本中提取关键工艺参数
- **置信度评分**: 提供解析结果的可靠性评估
- **警告机制**: 标识潜在问题和不确定的信息

## API端点

### POST `/api/v1/research/ai/parse-experiment`

解析实验记录文件内容。

**请求体:**
```json
{
  "content": "反应温度80°C，压力常压，时间4小时，收率85%",
  "parse_type": "lab_confirmation",
  "file_name": "experiment_001.txt"
}
```

**响应:**
```json
{
  "code": 200,
  "message": "实验记录解析成功",
  "data": {
    "parse_type": "lab_confirmation",
    "confidence": 0.92,
    "data": {
      "temperature": "80°C",
      "pressure": "常压",
      "time": "4小时",
      "yield_rate": 85.0
    },
    "warnings": []
  }
}
```

### POST `/api/v1/research/ai/parse-parameters`

解析工艺参数文本。

**请求体:**
```json
{
  "content": "反应温度80°C，压力常压，时间4小时",
  "parse_type": "lab_confirmation"
}
```

**响应:**
```json
{
  "code": 200,
  "message": "工艺参数解析成功",
  "data": {
    "parameters": {
      "temperature": "80°C",
      "pressure": "常压",
      "time": "4小时"
    },
    "confidence": 0.95,
    "warnings": []
  }
}
```

## 数据结构

### LabConfirmationParsedData (小试工艺确认)

- `temperature`: 反应温度
- `pressure`: 反应压力
- `time`: 反应时间
- `yield_rate`: 收率(%)
- `purity`: 纯度(%)
- `solvent`: 溶剂
- `catalyst`: 催化剂
- `raw_materials`: 原料列表
- `byproducts`: 副产物列表
- `observations`: 实验观察记录

### ScaleUpParsedData (放大生产)

- `batch_size`: 批次规模
- `equipment`: 使用设备
- `scale_factor`: 放大倍数
- `process_parameters`: 工艺参数字典
- `quality_metrics`: 质量指标字典
- `deviations`: 偏差记录列表
- `recommendations`: 建议事项列表

## 使用示例

### Python客户端

```python
import requests

# 解析实验记录
response = requests.post(
    "http://localhost:8000/api/v1/research/ai/parse-experiment",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={
        "content": "反应温度80°C，压力常压，时间4小时，收率85%",
        "parse_type": "lab_confirmation"
    }
)
result = response.json()
print(result["data"])
```

### TypeScript客户端

```typescript
import { parseExperimentRecord, parseProcessParameters } from '@/lib/api/server/ai'

// 解析实验记录
const result = await parseExperimentRecord(
  "反应温度80°C，压力常压，时间4小时，收率85%",
  "lab_confirmation"
)

// 解析工艺参数
const params = await parseProcessParameters(
  "反应温度80°C，压力常压，时间4小时",
  "lab_confirmation"
)
```

## 依赖项

- `app.core.llm`: LLM客户端（需要配置API密钥）
- Pydantic v2: 数据验证

## 注意事项

1. **LLM配置**: 确保在`.env`中正确配置了LLM提供商和API密钥
2. **内容长度限制**: 
   - 实验记录: 最多50,000字符
   - 工艺参数: 最多30,000字符
3. **解析类型**: 必须为`lab_confirmation`或`scale_up`
4. **置信度**: 低于0.7的结果应谨慎使用，建议人工复核

## 错误处理

模块会捕获以下异常：

- `ValueError`: 参数验证失败（如无效的parse_type）
- `LLMProviderError`: LLM提供商错误
- `LLMOutputError`: LLM输出格式错误
- 通用异常: 其他未预期的错误

所有错误都会返回适当的HTTP状态码和错误消息。
