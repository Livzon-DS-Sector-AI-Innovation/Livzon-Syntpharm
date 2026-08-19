"""AI Parser Schema和API结构测试（无需LLM）"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.modules.research.ai_parser.schemas import (
    ExperimentParseRequest,
    ExperimentParseResponse,
    LabConfirmationParsedData,
    ParameterParseRequest,
    ParameterParseResponse,
    ScaleUpParsedData,
)


def test_schemas():
    """测试Pydantic Schema"""
    print("=" * 60)
    print("AI Parser Schema 测试")
    print("=" * 60)

    # 1. 测试实验记录解析请求
    print("\n📋 测试 ExperimentParseRequest:")
    try:
        req = ExperimentParseRequest(content="温度80°C，时间4小时", parse_type="lab_confirmation")
        print("  ✅ 创建成功")
        print(f"     content: {req.content[:20]}...")
        print(f"     parse_type: {req.parse_type}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 2. 测试小试数据结构
    print("\n📋 测试 LabConfirmationParsedData:")
    try:
        data = LabConfirmationParsedData(
            temperature="80°C", pressure="常压", time="4小时", yield_rate=85.0, purity=98.5
        )
        print("  ✅ 创建成功")
        print(f"     温度: {data.temperature}")
        print(f"     收率: {data.yield_rate}%")
        print(f"     纯度: {data.purity}%")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 3. 测试放大生产数据结构
    print("\n📋 测试 ScaleUpParsedData:")
    try:
        data = ScaleUpParsedData(batch_size="100L", equipment="反应釜R-101", scale_factor=10.0)
        print("  ✅ 创建成功")
        print(f"     批次规模: {data.batch_size}")
        print(f"     设备: {data.equipment}")
        print(f"     放大倍数: {data.scale_factor}x")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 4. 测试实验记录解析响应
    print("\n📋 测试 ExperimentParseResponse:")
    try:
        lab_data = LabConfirmationParsedData(temperature="80°C")
        resp = ExperimentParseResponse(
            parse_type="lab_confirmation", confidence=0.92, data=lab_data, warnings=["数据不完整"]
        )
        print("  ✅ 创建成功")
        print(f"     解析类型: {resp.parse_type}")
        print(f"     置信度: {resp.confidence}")
        print(f"     警告数: {len(resp.warnings)}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 5. 测试工艺参数解析请求
    print("\n📋 测试 ParameterParseRequest:")
    try:
        req = ParameterParseRequest(content="反应温度80°C，压力常压", parse_type="lab_confirmation")
        print("  ✅ 创建成功")
        print(f"     content: {req.content[:20]}...")
        print(f"     parse_type: {req.parse_type}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 6. 测试工艺参数解析响应
    print("\n📋 测试 ParameterParseResponse:")
    try:
        resp = ParameterParseResponse(
            parameters={"temperature": "80°C", "pressure": "常压"}, confidence=0.95, warnings=[]
        )
        print("  ✅ 创建成功")
        print(f"     参数数: {len(resp.parameters)}")
        print(f"     置信度: {resp.confidence}")
        print(f"     警告数: {len(resp.warnings)}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False

    # 7. 测试验证规则
    print("\n📋 测试验证规则:")
    try:
        # 测试无效的parse_type
        ExperimentParseRequest(content="test", parse_type="invalid_type")
        print("  ❌ 应该拒绝无效的parse_type")
        return False
    except Exception:
        print("  ✅ 正确拒绝了无效的parse_type")

    try:
        # 测试空content
        ExperimentParseRequest(content="", parse_type="lab_confirmation")
        print("  ❌ 应该拒绝空content")
        return False
    except Exception:
        print("  ✅ 正确拒绝了空content")

    print("\n" + "=" * 60)
    print("✅ 所有Schema测试通过")
    print("=" * 60)
    return True


def test_api_routes():
    """测试API路由注册"""
    print("\n" + "=" * 60)
    print("AI Parser API 路由测试")
    print("=" * 60)

    try:
        from app.modules.research.ai_parser.api import router

        routes = [route.path for route in router.routes]
        print(f"\n🔗 找到 {len(routes)} 个路由:")

        expected_routes = ["/ai/parse-experiment", "/ai/parse-parameters"]
        for expected in expected_routes:
            if expected in routes:
                print(f"  ✅ {expected}")
            else:
                print(f"  ❌ {expected} (缺失)")
                return False

        print("\n✅ 所有API路由已正确注册")
        return True
    except Exception as e:
        print(f"\n❌ API路由测试失败: {e}")
        return False


if __name__ == "__main__":
    results = []
    results.append(test_schemas())
    results.append(test_api_routes())

    print("\n" + "=" * 60)
    if all(results):
        print("🎉 所有测试通过！AI Parser模块结构完整")
    else:
        print("❌ 部分测试失败")
    print("=" * 60)
