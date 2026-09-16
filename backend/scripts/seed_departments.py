"""初始化基础部门数据脚本。"""

import asyncio
import uuid
import sys

sys.path.insert(0, "/home/zhuangweizi/Livzon-Syntpharm/backend")

from app.core.database import async_session_factory
from app.modules.hr.models import HrDepartment
from sqlalchemy import select

# 根据飞书截图提取的核心部门结构
CORE_DEPARTMENTS = [
    {"name": "珠海保税区丽珠合成制药有限公司", "code": "LIZHU_SYNTHETIC"},
    {"name": "注册部", "code": "REG_DEPT"},
    {"name": "人事行政部", "code": "HR_ADMIN"},
    {"name": "非头孢制造部", "code": "NON_CEPH_MFG"},
    {"name": "头孢合成制造部", "code": "CEPH_SYN_MFG"},
    {"name": "财务部", "code": "FINANCE"},
    {"name": "生产部", "code": "PRODUCTION"},
    {"name": "技术研发部", "code": "R_AND_D"},
    {"name": "106车间", "code": "WS_106"},
    {"name": "AI创新部", "code": "AI_INNOVATION"},
    # 映射表中的标准部门
    {"name": "101车间", "code": "WS_101"},
    {"name": "102车间", "code": "WS_102"},
    {"name": "103车间", "code": "WS_103"},
    {"name": "设备工程部", "code": "ENG_DEPT"},
    {"name": "动力部", "code": "POWER_DEPT"},
    {"name": "质量控制部", "code": "QC_DEPT"},
    {"name": "质量保证部", "code": "QA_DEPT"},
    {"name": "安全环保部", "code": "HSE_DEPT"},
    {"name": "溶剂回收车间", "code": "SOLVENT_WS"},
    {"name": "仓库", "code": "WAREHOUSE"},
]


async def seed():
    print("🌱 开始初始化基础部门数据...")
    async with async_session_factory() as db:
        for dept_info in CORE_DEPARTMENTS:
            # 检查是否已存在
            result = await db.execute(select(HrDepartment).where(HrDepartment.name == dept_info["name"]))
            if not result.scalar_one_or_none():
                new_dept = HrDepartment(
                    id=uuid.uuid4(), name=dept_info["name"], code=dept_info["code"], is_deleted=False
                )
                db.add(new_dept)
                print(f"   ➕ 创建部门: {dept_info['name']}")
            else:
                print(f"   ✅ 部门已存在: {dept_info['name']}")

        await db.commit()
        print("🎉 部门种子数据初始化完成！")


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)
