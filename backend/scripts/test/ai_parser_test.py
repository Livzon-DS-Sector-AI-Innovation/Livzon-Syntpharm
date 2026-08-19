"""AI Parser模块测试脚本"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.modules.research.ai_parser.service import parse_experiment_record, parse_process_parameters


async def test_parse_experiment():
    """测试实验记录解析"""
    print("🧪 测试实验记录解析...")
    
    content = """
    实验记录 - 小试工艺确认
    
    反应条件：
    - 温度：80°C
    - 压力：常压
    - 时间：4小时
    - 溶剂：乙醇
    - 催化剂：Pd/C
    
    结果：
    - 收率：85%
    - 纯度：98.5%
    
    观察：反应平稳，无明显副产物生成
    """
    
    try:
        result = await parse_experiment_record(content, "lab_confirmation")
        print(f"✅ 解析成功")
        print(f"   置信度: {result.confidence}")
        print(f"   温度: {result.data.temperature}")
        print(f"   收率: {result.data.yield_rate}%")
        print(f"   警告: {result.warnings}")
        return True
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        return False


async def test_parse_parameters():
    """测试工艺参数解析"""
    print("\n🧪 测试工艺参数解析...")
    
    content = "反应温度80°C，压力常压，时间4小时，使用乙醇作为溶剂"
    
    try:
        result = await parse_process_parameters(content, "lab_confirmation")
        print(f"✅ 解析成功")
        print(f"   置信度: {result.confidence}")
        print(f"   参数: {result.parameters}")
        print(f"   警告: {result.warnings}")
        return True
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        return False


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("AI Parser 模块测试")
    print("=" * 60)
    
    results = []
    results.append(await test_parse_experiment())
    results.append(await test_parse_parameters())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ 所有测试通过")
    else:
        print("❌ 部分测试失败")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
