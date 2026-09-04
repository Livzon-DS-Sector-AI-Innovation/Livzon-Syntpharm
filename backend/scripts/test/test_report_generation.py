"""
离线测试报告生成核心逻辑
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.modules.research.service import calculate_doe_conclusions, fill_template_slots, validate_report_content

# 模拟数据库查询返回的数据
MOCK_PROJECT = {
    "id": "723537bc-f797-469e-9c93-d70301c74447",
    "name": "阿莫西林原料药工艺优化",
    "api_name": "Amoxicillin",
    "cas_number": "26787-78-0",
}

MOCK_DOE_DATA = {
    "runs": [
        {"status": "completed", "response_values": {"yield": 75.0}},
        {"status": "completed", "response_values": {"yield": 82.5}},
        {"status": "completed", "response_values": {"yield": 85.3}},  # 峰值
        {"status": "completed", "response_values": {"yield": 80.1}},
    ],
    "responses": [{"name": "yield", "unit": "%"}],
    "analysis_result": {"optimal_conditions": {"temperature": 80, "time": 4}, "r_squared": 0.95},
}

# 模拟模板内容
MOCK_TEMPLATE = """
# {{F:project_name}} 研发报告

## 1. 基础信息
- **API**: {{F:api_name}}
- **CAS**: {{F:cas_number}}

## 2. 实验结论
根据 DOE 分析，{{B:yield_summary}}。
模型拟合度为 {{B:model_fit_evaluation}}。
最优条件为：温度 {{F:doe_optimal_temperature}}°C，时间 {{F:doe_optimal_time}}h。

## 3. AI 讨论区
{{P:mechanism_discussion}}
"""


async def main():
    print("🚀 开始离线测试报告生成逻辑...")

    # 1. 构建 Fact 字典 (模拟)
    print("\n[1] 构建 Fact 字典...")
    facts = {
        "project_name": {"value": MOCK_PROJECT["name"], "unit": "", "source_id": MOCK_PROJECT["id"]},
        "api_name": {"value": MOCK_PROJECT["api_name"], "unit": "", "source_id": MOCK_PROJECT["id"]},
        "cas_number": {"value": MOCK_PROJECT["cas_number"], "unit": "", "source_id": MOCK_PROJECT["id"]},
        "doe_optimal_temperature": {"value": 80, "unit": "°C", "source_id": "DOE-001"},
        "doe_optimal_time": {"value": 4, "unit": "h", "source_id": "DOE-001"},
    }
    print(f"   ✅ 已提取 {len(facts)} 个硬事实。")

    # 2. 计算派生结论
    print("\n[2] 计算派生结论 (Derived Facts)...")
    derived_facts = calculate_doe_conclusions(MOCK_DOE_DATA)
    print(f"   ✅ 已生成 {len(derived_facts)} 个结论标签。")
    print(f"   - 收率趋势: {derived_facts.get('yield_summary', {}).get('trend')}")
    print(f"   - 模型评价: {derived_facts.get('model_fit_evaluation', {}).get('quality_label')}")

    # 3. 槽位填充
    print("\n[3] 执行槽位填充...")
    filled_text, prose_slots = fill_template_slots(MOCK_TEMPLATE, facts, derived_facts)
    print("   ✅ 已填充 Fact/B 类槽位。")
    print(f"   ⏳ 剩余 Prose 槽位待 AI 补全: {prose_slots}")

    # 4. 模拟 AI 补全 (这里用固定文本代替)
    final_report = filled_text.replace(
        "{{P:mechanism_discussion}}",
        "本次实验通过响应面法确定了关键工艺参数。数据显示在 80°C 时反应效率最高，符合阿伦尼乌斯方程预期。",
    )

    # 5. 校验
    print("\n[4] 运行数值校验...")
    validation = validate_report_content(final_report, facts)
    if validation["passed"]:
        print("   ✅ 校验通过！")
    else:
        print(f"   ⚠️ 校验警告: {validation['warnings']}")

    print("\n" + "=" * 50)
    print("📄 生成的报告预览:")
    print("=" * 50)
    print(final_report)


if __name__ == "__main__":
    asyncio.run(main())
