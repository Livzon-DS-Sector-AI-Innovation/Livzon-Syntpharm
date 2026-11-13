# AI 联网检索能力调研结论

> 调研日期：2026-11-10
> 结论：**平台当前 AI 不支持联网检索**，但有 3 条可行的接入路径。

## 现状

- LLM 调用走 `backend/app/core/llm/client.py` 的 `LLMClient`，仅提供 `chat / chat_json / chat_vision / chat_vision_json` 四个方法
- 请求体只包含 `model / messages / temperature / max_tokens / response_format`，**没有 tools / function calling / web_search 参数**
- 底层走公司代理 `https://newapi.livzon.cn/v1`（OpenAI 兼容协议），当前模型 `deepseek-v4-pro`
- MCP server（`app/platform/mcp/server.py`）只挂载了 equipment 模块的工具，无搜索类工具

因此目前所有 AI 功能（验证审核、发补回复、法规解读等）都只能用模型训练数据里的知识，无法获取实时信息。

## 三条接入路径

### 路径 A：验证 newapi 代理上游的联网插件（成本最低，先验证）

newapi（one-api 系）中转站通常支持透传上游模型的厂商插件能力。DeepSeek 官方 API 本身**没有**联网开关，但如果代理上游配置了带联网的模型（如带 `enable_search` 的通义千问、或 Perplexity 系模型），可以直接换模型或加参数透传。

**验证方法**：用现有 `LLM_API_KEY` 直接 curl 代理：
```bash
curl -X POST https://newapi.livzon.cn/v1/chat/completions \
  -H "Authorization: Bearer $LLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v4-pro", "messages": [{"role": "user", "content": "今天的新闻头条是什么"}]}'
```
再问一个超出模型知识截止的问题，看回答是否包含实时信息。也可问代理管理员是否支持 `web_search` / `enable_search` 透传参数。

**工作量**：若支持，仅需在 `llm/client.py` 的 body 里加一个可配置参数，约 20 行代码。

### 路径 B：自建搜索工具 + Function Calling（可控性强，推荐）

在 `llm/client.py` 增加 `chat_with_tools` 方法，接入第三方搜索 API：

| 搜索服务 | 特点 | 成本 |
|---|---|---|
| Tavily | 专为 LLM 设计，返回摘要化结果 | 免费 1000 次/月 |
| SerpAPI | Google 结果，稳定 | 付费，$50/月起 |
| Bing Web Search API | 微软官方 | 免费额度 1000 次/月 |
| 博查（bochaai）| 国内服务，中文友好，无需翻墙 | 有免费额度 |

流程：用户问题 → LLM 判断需要联网 → 调搜索工具 → 结果塞回上下文 → LLM 生成带引用的回答。

**工作量**：llm client 扩展 + 搜索工具封装 + 至少一轮 tool-call 循环处理，约 1-2 天。

### 路径 C：MCP 挂载 web_search 工具（架构最规范）

在 `app/platform/mcp/` 下注册 `@mcp.tool() web_search`，供 AI Agent 类功能（dossier_writer 的 ai_fill 等）调用。

**注意**：当前平台的 MCP server 是**对外提供服务**（`/mcp` 端点给外部 agent 用），不是给内部 LLM 调用链用的。要让内部 LLM 用上 MCP 工具，还需要在业务代码里实现 MCP client 调用或手动把工具定义传给 LLM——绕了一圈，不如路径 B 直接。

## 建议

1. **先做路径 A 的验证**（半天）：如果代理支持联网透传，成本几乎为零
2. 不支持则走**路径 B**，优先选博查或 Tavily（中文场景 + 免翻墙）
3. 联网能力建议做成**模块级可配置开关**（`core.llm_configs` 已有配置表），法规跟踪（regulatory_tracker）是最大受益场景——AI 解读法规时能联网核对原文，可大幅减少幻觉

## 与本次注册模块优化的关系

本次审评进度预测采用的是「规则推算 + 历史统计修正」，不依赖联网检索。AI 联网属于独立增强项，建议单独立项。
