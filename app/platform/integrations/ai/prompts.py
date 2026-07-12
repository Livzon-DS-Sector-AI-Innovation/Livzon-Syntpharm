"""通用 AI 提示词构建工具。


提供跨模块复用的 prompt 构建基础设施。
模块特定的提示词配置应放在各自模块内部（如 app/modules/<module>/ai_prompts.py）。
"""

from typing import Any


def build_prompt(workflow_config: dict[str, Any]) -> str:
    """将结构化提示词合并为完整 prompt，供 AI Agent 使用。

    支持两种配置格式：
    - 新格式: {input_info} + {work_rules} + {reference_docs} + {output_format}
    - 旧格式: {prompt_template} 或 {prompt}

    这样前端保存的 4 字段结构化配置和硬编码 fallback 的单一 prompt 都能正常工作。
    """
    parts = []

    # 新格式：4 字段结构化配置
    if "input_info" in workflow_config:
        parts.append(workflow_config["input_info"])

    if "work_rules" in workflow_config:
        parts.append("## 工作规则\n" + workflow_config["work_rules"])

    if "reference_docs" in workflow_config:
        ref = workflow_config["reference_docs"]
        if isinstance(ref, dict):
            ref_text = ref.get("text", "")
            if ref_text:
                parts.append("## 参考文档\n" + ref_text)
        elif isinstance(ref, str) and ref:
            parts.append("## 参考文档\n" + ref)

    if "output_format" in workflow_config:
        parts.append("## 输出格式\n" + workflow_config["output_format"])

    # 如果有新格式字段，返回合并结果
    if parts:
        return "\n\n".join(parts)

    # 旧格式：单一 prompt 或 prompt_template
    return workflow_config.get("prompt_template") or workflow_config.get("prompt", "")  # type: ignore[no-any-return]
