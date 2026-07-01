"""法规影响判定规则知识库。

提供 YAML 配置文件的加载和缓存，供 AI Prompt 和校验逻辑使用。
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# 知识库目录
KNOWLEDGE_DIR = Path(__file__).parent

# 缓存
_cache: dict[str, Any] = {}


def _load_yaml(filename: str) -> dict:
    """加载 YAML 文件，带缓存。"""
    if filename in _cache:
        return _cache[filename]

    filepath = KNOWLEDGE_DIR / filename
    if not filepath.exists():
        logger.warning(f"Knowledge file not found: {filepath}")
        return {}

    try:
        with open(filepath, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        _cache[filename] = data
        return data
    except Exception as e:
        logger.error(f"Failed to load knowledge file {filepath}: {e}")
        return {}


def get_impact_rules() -> dict:
    """获取影响判定规则。"""
    return _load_yaml("impact_rules.yaml")


def get_keyword_rules() -> dict:
    """获取关键词规则。"""
    return _load_yaml("keyword_rules.yaml")


def get_action_guidance() -> dict:
    """获取建议行动模板。"""
    return _load_yaml("action_guidance.yaml")


def get_all_rules() -> dict:
    """获取所有规则。"""
    return {
        "impact_rules": get_impact_rules(),
        "keyword_rules": get_keyword_rules(),
        "action_guidance": get_action_guidance(),
    }


def build_prompt_summary() -> str:
    """构建 Prompt 中使用的规则摘要。

    将 YAML 规则转换为简洁的文本摘要，供 AI Prompt 引用。
    """
    impact_rules = get_impact_rules()
    get_keyword_rules()
    action_guidance = get_action_guidance()

    lines = []

    # 高影响法规主题
    lines.append("## 默认高影响法规（直接涉及原料药/API）")
    lines.append("以下法规主题默认 impact_level=high, relevance_level=related：")
    for rule in impact_rules.get("high_impact_rules", []):
        keywords_str = "、".join(rule.get("keywords", [])[:5])
        lines.append(f"- {rule['topic']}（关键词：{keywords_str}）")

    # 中影响法规主题
    lines.append("")
    lines.append("## 默认中影响法规（通用要求类）")
    lines.append(
        "以下法规主题默认 impact_level=medium, relevance_level=related 或 weak_related："
    )
    for rule in impact_rules.get("medium_impact_rules", []):
        keywords_str = "、".join(rule.get("keywords", [])[:5])
        lines.append(f"- {rule['topic']}（关键词：{keywords_str}）")

    # 低影响法规及升级条件
    lines.append("")
    lines.append("## 默认低影响法规（可升级）")
    lines.append("以下法规主题默认 impact_level=low, relevance_level=weak_related。")
    lines.append("如果正文包含升级条件中的关键词，影响等级升级为 medium：")
    for rule in impact_rules.get("low_impact_rules", []):
        keywords_str = "、".join(rule.get("keywords", [])[:5])
        lines.append(f"- {rule['topic']}（关键词：{keywords_str}）")
        for upgrade in rule.get("upgrade_conditions", []):
            upgrade_kw = "、".join(upgrade.get("keywords", [])[:3])
            lines.append(f"  升级条件：包含 {upgrade_kw} → 升级为 medium/related")

    # 无影响法规及升级条件
    lines.append("")
    lines.append("## 默认无影响法规（可升级）")
    lines.append("以下法规主题默认 impact_level=none, relevance_level=unrelated。")
    lines.append("如果正文包含升级条件中的关键词，影响等级升级为 low/weak_related：")
    for rule in impact_rules.get("none_impact_rules", []):
        keywords_str = "、".join(rule.get("keywords", [])[:5])
        lines.append(f"- {rule['topic']}（关键词：{keywords_str}）")
        for upgrade in rule.get("upgrade_conditions", []):
            upgrade_kw = "、".join(upgrade.get("keywords", [])[:3])
            lines.append(f"  升级条件：包含 {upgrade_kw} → 升级为 low/weak_related")

    # 建议行动模板
    lines.append("")
    lines.append("## 建议行动措辞要求")
    lines.append("所有建议行动必须使用评估型表达，禁止使用命令式表达。")
    lines.append("")
    lines.append("正确示例：")
    assessment_verbs = action_guidance.get("assessment_verbs", [])
    for verb in assessment_verbs[:5]:
        lines.append(f"- {verb}...")
    lines.append("")
    lines.append("错误示例（禁止使用）：")
    forbidden = action_guidance.get("forbidden_expressions", [])
    for expr in forbidden[:5]:
        lines.append(f"- {expr}")

    return "\n".join(lines)


def clear_cache():
    """清除缓存（用于测试或规则更新后）。"""
    global _cache
    _cache = {}
